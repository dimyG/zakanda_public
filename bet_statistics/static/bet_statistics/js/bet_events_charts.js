/**
 * Created by xene on 4/25/2016.
 */

define([
    'd3',
    'crossfilter',
    'dc',
    'js/utils',
    'js/urls',
    'moment',
    'js/libs/colorbrewer'
], function(d3, crossfilter, dc, Utils, Urls, Moment, colorbrewer){

    var config = {
        debug: Utils.config.logger.bet_statistics,
        tb_bev_array_names: {
            // total_bets and bet_events arrays (arrays of objects) have been joined. Each total_bet object now has some additional properties which
            // are the data of the bet_events that it contains. These are the names of these properties. So a tb obj has a markets property
            markets: "markets",
            choices: "bet_event_choices"
            //bet_event_statuses: "bet_event_statuses",
            //bet_event_choices: "bet_event_choices",
            //home_teams: "home_teams",
            //away_teams: "away_teams",
            //competitions: "competitions",
            //countries: "countries"
        },
        //month_names: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ],
        //day_names: ['Mon', 'Tue', 'Wen', 'Thu', 'Fri', 'Sat', 'Sun'],
        urls: Urls,
        chart_ids: ["#bet_events_market_pie", "#bet_events_choice_pie", "#bet_events_status_pie"],
        pie_width: 300,
        pie_height: 170,
        min_width_pie: 100,
        max_width_pie: 200
        //bev_server_names: {
        //    // the properties of a bet_event object from the bet_events array. These names are defined by the pandas dataframe renaming in the server
        //    market_type: "market_type",
        //    bet_event_status: "selection_status",
        //    bet_event_choice: "choice",
        //    home_team: "home_team",
        //    away_team: "away_team",
        //    competition: "competition_generic_name",
        //    country: "country"
        //}
    };

    var log = Utils.create_logger(config.debug);
    var glog = Utils.logger();
    var tb_markets_array_name = config.tb_bev_array_names.markets;
    var tb_choices_array_name = config.tb_bev_array_names.choices;
    var urls = config.urls;
    var date_format = "ddd DD MMM YYYY HH:mm";
    var chart_ids = config.chart_ids;
    var charts = {};
    var won_str = Utils.config.status.Won;
    var lost_str = Utils.config.status.Lost;
    var void_str = Utils.config.status.Void;
    var won_class = Utils.config.status_class.won;
    var lost_class = Utils.config.status_class.lost;
    var void_class = Utils.config.status_class.void;
    var next = null;
    var last = null;


    function bind_events(){
        $(document).on('click', chart_ids[0] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[0]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[1] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[1]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[2] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[2]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', "input.bev_dc_table_next", function(e){
            next();
        });
        $(document).on('click', "input.bev_dc_table_last", function(e){
            last();
        });
    }

    function to_counter_object(array){
        var obj = {};
        for (var i=0; i<array.length; i++){
            obj[array[i]] = (obj[array[i]] || 0) + 1;
        }
        return obj; // {bev_id_1: 2, bev_id_2: 4, ... bev_id_n: 1}
    }

    function patch_filterHandler(chart){
        // the filterHandler is needed for the case in which we want to filter the other charts based on a filter from the bet_events pie
        //
        // Without the custom filterHandler:
        // You select the "Full Time Result" slice. The The filters array is now ["Full Time Result"].
        // This filter would "select" all the total bets the markets array of which is ["Full Time Result"]. A total bet with
        // markets array ["Full Time Result", "Full Time Result"] would not be "selected" and wouldn't appear in the chart despite the
        // fact that you have selected the "Full Time Result" slice and this total bet has bet events with "Full Time Result" markets.
        //
        // With the custom filterHandler:
        // You loop through the whole markets array. Example: You select the "Full Time Result" slice. The filters array is now
        // ["Full Time Result"]. You loop through the markets array of each total bet. If one value of the markets array is in the
        // filters array, then we return true for this total bet and it appears in the chart.
        chart.filterHandler (function (dimension, filters) {
            dimension.filter(null);
            if (filters.length === 0)
                dimension.filter(null);
            else
                dimension.filterFunction(function (d) {
                    // In case of markets dimension, d is the markets array of each total bet. ["Full Time Result", "Full Time Result"] etc
                    for (var i=0; i < d.length; i++) {
                        if (filters.indexOf(d[i]) >= 0) return true;
                    }
                    return false;
                });
            return filters;
        });
    }

    function array_to_values_custom_reduce(array, crossfilter){
        // The goal is to count all the separate values of an array of a dimension in the grouping.
        // In this case I have added some variables in the total bets array. These variables are the data of the bet events
        // that a total bet contains. They are arrays. For example each total bet, now has a "markets" array that contains the
        // markets of its bet_events. I want to create a dimension from the markets. But I want the grouping to take into account
        // the unique values of the array and not the array as a whole (If a total bet markets array is ["Full Time Res", "Double Chance"]
        // a slice of the pie would be "Full Time Res" and another one "Double Chance" and not having one slice for both).
        //
        // At the end we also have to patch the filterHandler method of the group to achieve proper reverse filtering.
        function reduceAdd(p, v) {
            v[array].forEach (function(val, idx) {
                p[val] = (p[val] || 0) + 1; //increment counts
            });
            return p;
        }

        function reduceRemove(p, v) {
            v[array].forEach (function(val, idx) {
                p[val] = (p[val] || 0) - 1; //decrement counts
            });
            return p;
        }

        function reduceInitial() {
            return {};
        }

        var values_dimension = crossfilter.dimension(function(d){return d[array]});
        var byValuesGroup = values_dimension.groupAll().reduce(reduceAdd, reduceRemove, reduceInitial).value();
        // byValuesGroup.value() -- > {'Full Time Result': 17, 'Double Chance': 3, 'Over Under 2.5': 6} It refers to bet events not total bets

        // patch group's all and top methods
        byValuesGroup.all = function() {
          var newObject = [];
          for (var key in this) {
            if (this.hasOwnProperty(key) && key != "all" && key != "top") {
              newObject.push({
                key: key,
                value: this[key]
              });
            }
          }
          return newObject;
          //[ {key: 'Full Time Result', value: 17}, {key: 'Double Chance', value: 3}, {key: 'Over Under 2.5', value: 6} ]
        };

        byValuesGroup.top = function(count) {
            var newObject = this.all();
            newObject.sort(function(a, b){return b.value - a.value});
            return newObject.slice(0, count);
        };

        return [values_dimension, byValuesGroup]
    }

    // For filtering total_bet_cf from bet_event_cf - Not currently in use

    //function tb_ids_from_bev_array_value(filters, tb_bev_array_name, tb_ids_dim){
    //    // used to filter a total bets dim from the bet events charts. You have to create a total bet dim from the total bet ids.
    //    // The concept is that you maually filter the total bets dim based on the filters of the bet event charts.
    //    // You can use this function along with the filter_tb_dim() one in a patched filterHandler method of
    //    // the bet events chart. The  filterHandler is the default one. You just have to add these function calls.
    //    // It works. It filters the total bet charts but the problem is that it filters also the market pie chart that
    //    // filters again the bet events charts with its on pretransition event. So you need to use a module level boolean
    //    // variable to determine when to filter the bet_events charts from the markets pie.
    //    var tb_ids = [];
    //    tb_ids_dim.filterAll();
    //    var tbs = tb_ids_dim.top(Infinity);
    //    log('tbs' + tbs + ' filters' + filters);
    //    for (var i=0; i<tbs.length; i++){
    //        var tb = tbs[i];
    //        if (filters.length){
    //            var tb_bev_array = tb[tb_bev_array_name];
    //            log(tb_bev_array);
    //            for(var j=0; j<tb_bev_array.length; j++){
    //                if (filters.indexOf(tb_bev_array[j]) >= 0){
    //                    log(filters + 'filters matched');
    //                    tb_ids.push(tb.total_bet_id);
    //                    break;
    //                }
    //            }
    //        }else{
    //            tb_ids.push(tb.total_bet_id);
    //        }
    //    }
    //    log('tb_ids', tb_ids);
    //    return tb_ids
    //}
    //function filter_tb_dim(tb_ids_dim, tb_ids){
    //    //if (tb_ids_dim.top(Infinity).length != tb_ids.length){
    //        tb_ids_dim.filterFunction(function(d){
    //            log('d',d);
    //            if (tb_ids.indexOf(d) >= 0){
    //                log('filtered d', d);
    //                return d
    //            }
    //        });
    //    //}
    //}

    function get_active_bev_ids(chart, tb_bev_array_name){
        // It returns the bet events of the active total bets based on the active filters of the chart.
        // For example for the bev markets pie. It gets all the total bets of the pie. From each one it takes its bet events markets.
        // If the chart has an active filter (like Full Time Result) then it will return only the respective bet_events.
        // if a bev is used by many tbs then the returned array will contain the respective bev as many times as it is used
        var active_total_bets = chart.dimension().top(Infinity);
        log("active_total_bets from market pie", active_total_bets);
        var filters = chart.filters();
        var active_bet_event_ids = [];
        for (var i=0; i<active_total_bets.length; i++){
            var tb_bev_array = active_total_bets[i][tb_bev_array_name];
            var bev_ids = [];
            if (filters.length){
                for (var j = 0; j < tb_bev_array.length; j++) {
                    if (filters.indexOf(tb_bev_array[j]) >= 0) {
                        //We get those bev ids the market of which is in the filtered markets
                        bev_ids.push(active_total_bets[i].bet_event_ids[j])
                    }
                }
            }else{
                bev_ids = active_total_bets[i].bet_event_ids;
            }
            active_bet_event_ids.push.apply(active_bet_event_ids, bev_ids); // extend active_bet_event_ids array
        }
        log('respective active_bet_event_ids', active_bet_event_ids);
        return active_bet_event_ids
    }

    function filter_bevs_dim(tb_ids_dim, tb_ids_bev_dim){
        // manually filters the bet events dimension so it returns bet events that belong to the given total bets dim
        // Notice that if a bev appears in more than one total bets, it will be returned many times.
        // if a bet event appears more than one time in the active bet events (meaning that it has been "betted" more than one times)
        // then we must filter the bet events dim but taking this into account. So the dim will have this bet event more than on times.
        tb_ids_bev_dim.filterFunction(function(d){
            // d is the total bet id. The filtering returns bet event objects since tb_ids_bev_dim is on bev crossfilter
            var tb = $.grep(tb_ids_dim.top(Infinity), function(e){return e.total_bet_id == d; })[0];
            if (tb){
                return d;
            }
        });
        //console.debug('POST bet_event_ids_dim', bet_event_ids_dim.top(Infinity));
    }

    function bet_events_market_pie(market_pie, total_bets_cf, tb_ids_dim, tb_ids_bev_dim){
        // The bev ids dimension is used only for manual filtering, not directly by a chart

        // The concept is that we manually filter the bet events dim and all the charts that use the bet events cf are
        // filtered by it. We don't use it directly in any chart.
        // We create the bet event charts (except from the markets chart) from the bet_events_cf.
        // So if we filter manually its bev ids dim, the charts associated with the bet_events_cf will be filtered.
        // We apply 2 additional "filters":
        // 1. We get the bet event ids from the filtered total bets. We get those bev ids the market of which is
        // in the filtered markets (the markets pie filters).
        // 2. We keep in an object a record of how many times each bet_event appears in the filtered total bets
        // (the total bets of the markets pie dimension). Then when we filter the bev ids dim, we return each
        // bet event id as many times as it exists in the object.
        // These actions are applied on pretransition event of the market pie. So every time the chart changes the bet events dim
        // is manually filtered.
        // IMPORTANT:
        // Notice that this chart must be the last one to be created in order its rendering to affect all
        // the charts that use the bet_events_cf.

        var result = array_to_values_custom_reduce(tb_markets_array_name, total_bets_cf);
        var betEventsMarketDim = result[0];
        var byMarket = result[1];

        //var betEventsMarketDim = bet_events_cf.dimension(function (d) {return d.market_type;});
        //var byMarket = betEventsMarketDim.group().reduceCount();
        //var all = bet_events_cf.groupAll().value();

        // we don't exclude the self from closest so the self is selected. This because the chart divs have
        // col class which defines their place inside a row. So if I took the parent the width would be the
        // width of the whole row.
        var width = $('#bet_events_market_pie').closest('div').width();
        width = 0.8*width;
        width = Utils.trim_value(width, config.max_width_pie, config.min_width_pie);
        var height = null;
        var inner_radius = width/6;
        //var width = config.pie_width;
        //var height = config.pie_height;
        market_pie
            .width(width).height(height)
            //.cx(width/2-(width/10))
            //.externalRadiusPadding(5)
            .innerRadius(inner_radius)
            .slicesCap(5)
            .controlsUseVisibility(true)
            //.legend(dc.legend().x(1.96/3*width).y(10).gap(5).legendText(function(d){
            //    return d.name
            //}))
            .label(function(d){
                //return d.key + ' ' + d.value;
                var all = 0;
                for (var j=0; j<byMarket.all().length; j++){all += byMarket.all()[j].value;}
                return d.key
                    +' ' + Math.floor(d.value / all * 100) + '%';
            })
            //.label(function (d) {
            //    if (status_pie.hasFilter() && !status_pie.hasFilter(d.key)) {
            //        return d.key + ' [0%]';
            //    }
            //    var label = d.key;
            //    if (all.value()) {
            //        label += ' [' + Math.floor(d.value / all.value() * 100) + '%]';
            //    }
            //    return label;
            //})
            .title(function(d){
                var all = 0;
                for (var j=0; j<byMarket.all().length; j++){all += byMarket.all()[j].value;}
                return d.key
                    +"\n"+ d.value + " bet events"
                    +' (' + Math.floor(d.value / all * 100) + '%)';
            })
            // DARK THEME
            // .on("renderlet", function(chart){
            //     chart.selectAll("text.pie-slice").style("fill", "#000000");
            // })
            .dimension(betEventsMarketDim)
            .group(byMarket)
            .ordering(function(d){return -d.value})
            //.ordinalColors(colorbrewer.Dark2[6])
            .colors(d3.scale.category10())
            //.colorAccessor(function(d){
            //    return d.value;
            //})
            ////.colorDomain([0, 50]);
            //.calculateColorDomain();

            .on('pretransition.monitor', function(chart, filter) { // monitor is just a namespace
                // This pie actually filters total bets. If you select goals over under 2.5 then it will return all
                // the bet events that are part of total bets with o/u 2.5 bet events. Instead of returning only
                // the o/u 2.5 bet events.
                //var active_bet_event_ids = get_active_bev_ids(chart, tb_markets_array_name);
                //var obj = to_counter_object(active_bet_event_ids);
                filter_bevs_dim(tb_ids_dim, tb_ids_bev_dim);
            });

        patch_filterHandler(market_pie);

        charts[chart_ids[0]] = market_pie;
        return market_pie;
    }

    function bet_events_choice_pie(choice_pie, betEventsChoiceDim){
        //With the following dim and group, the chart will be connected to the total_bet_cf similar to the market pie chart
        //var result = array_to_values_custom_reduce(config.bev_arrays.bet_event_choices, total_bets_cf);
        //var betEventsChoiceDim = result[0];
        //var byChoice = result[1];

        var byChoice = betEventsChoiceDim.group().reduceCount();

        var width = $('#bet_events_choice_pie').closest('div').width();
        width = 0.8*width;
        width = Utils.trim_value(width, config.max_width_pie, config.min_width_pie);
        var height = null;
        var inner_radius = width/6;
        //var width = config.pie_width;
        //var height = config.pie_height;
        choice_pie
            .width(width).height(height)
            //.cx(width/2-(width/10))
            //.externalRadiusPadding(5)
            .innerRadius(inner_radius)
            //.legend(dc.legend().x(2.1/3*width).y(10).gap(5))
            .slicesCap(5)
            .controlsUseVisibility(true)
            .label(function(d) {
                //return d.key + ' (' +  d.value + ')'
                var all = betEventsChoiceDim.top(Infinity).length;
                var text = d.key;
                if (d.key==="1"){text='Home'}else if(d.key==='2'){text='Away'}else if(d.key==='X'){text='Draw'}
                return text
                    +' ' + Math.floor(d.value / all * 100) + '%';
            })
            .title(function(d){
                var all = betEventsChoiceDim.top(Infinity).length;
                var text = d.key;
                if (d.key==="1"){text='Home'}else if(d.key==='2'){text='Away'}else if(d.key==='X'){text='Draw'}
                return text
                    +"\n"+ d.value + " bet events"
                    +' (' + Math.floor(d.value / all * 100) + '%)';
            })
            .minAngleForLabel(0.4)
            .dimension(betEventsChoiceDim)
            .group(byChoice)
            .ordering(function(d){ return -d.value })
            //.ordinalColors(colorbrewer.Dark2[6]);
            .colors(d3.scale.category10());

        //patch_filterHandler(choice_pie);
        charts[chart_ids[1]] = choice_pie;
        return choice_pie
    }

    function bet_events_status_pie(status_pie, betEventsStatusDim){
        //With the following dim and group, the chart will be connected to the total_bet_cf similar to the market pie chart
        //var result = array_to_values_custom_reduce(config.bev_arrays.bet_event_statuses, total_bets_cf);
        //var betEventsStatusDim = result[0];
        //var byStatus = result[1];

        var byStatus = betEventsStatusDim.group().reduceCount();

        var width = $('#bet_events_status_pie').closest('div').width();
        width = 0.8*width;
        width = Utils.trim_value(width, config.max_width_pie, config.min_width_pie);
        var height = null;
        var inner_radius = width/6;
        //var width = config.pie_width;
        //var height = config.pie_height;
        status_pie
            .width(width).height(height)
            //.cx(width/2-(width/10))
            //.externalRadiusPadding(5)
            .innerRadius(inner_radius)
            .controlsUseVisibility(true)
            //.legend(dc.legend().x(2.1/3*width).y(10).gap(5))
            .label(function(d) {
                //return d.key +" "+ d.value;
                var all = betEventsStatusDim.top(Infinity).length;
                return d.key
                    +' ' + Math.floor(d.value / all * 100) + '%';
            })
            .title(function(d){
                var all = betEventsStatusDim.top(Infinity).length;
                return d.key
                    +"\n"+ d.value + " bet events"
                    +' (' + Math.floor(d.value / all * 100) + '%)';
            })
            .dimension(betEventsStatusDim)
            .group(byStatus)
            .ordering(function(d){ return -d.value })
            //.colors(d3.scale.category10());
            .colors(d3.scale.ordinal().range([d3.rgb("#FF0000").darker(0.3).toString(),
                d3.rgb("#008000").brighter(0.5).toString(), d3.rgb("#3182bd").toString(), d3.rgb("#7b7a7a").toString()]))
            .colorDomain([0,1,2,3])
            .colorAccessor(function(d, i){
                if (d.key === 'Lost'){
                    return 0
                }else if (d.key === 'Won'){
                    return 1
                }else if(d.key === 'Open'){
                    return 2
                }else{ // if Void
                    return 3
                }
            });

        //patch_filterHandler(status_pie);

        charts[chart_ids[2]] = status_pie;
        return status_pie
    }

    function status_color_class(status){
        var color_class = "";
        if (status == won_str){
            color_class = 'won'
        }else if(status == lost_str){
            color_class = 'lost'
        }else{
            color_class = 'label-primary'
        }
        return color_class
    }

    function paginate(){

    }


    bet_events_table = function bev_table(event_date_dim, bev_table, total_bets, tb_ids_dim){
        //console.debug('tb_ids_dim.top(Infinity)', tb_ids_dim.top(Infinity));
        var fmt = d3.format('09d');
        bev_table
            .dimension(event_date_dim)
            // Data table does not use crossfilter group but rather a closure as a grouping function
            .group(function (d) {
                // I could use tb_ids_dim.top instead of crossfilter but I'm not sure which one is faster
                var tb = $.grep(total_bets, function(e){return e.total_bet_id === d.total_bet_id; })[0];

                var tb_date = Moment(tb.date).format(date_format);
                var tb_url = urls.stats.total_bet_detail + d.total_bet_id +"/";
                var color_class = status_color_class(tb.status);
                // var tb_text =
                //     '<table class="table table-condensed parent_tb">' + '<tbody>' + '<tr>' +
                //     '<td>' + "<a href='" + tb_url + "' class='pjax_call url_param_dependent'>" + '<span class="label label-sm tb_group_status ' + color_class + ' ">' + tb.status + '</span>' + "</a>" + '</td>' +
                //     '<td class="dc_tb_col">' + '<span class="label label-sm black">' + tb_date + '</span>' + '</td>' +
                //     '<td class="dc_tb_col">' + '<span class="label label-sm black">' + ' stake: ' + tb.amount.toFixed(3) + '</span>' + '</td>' +
                //     '<td class="dc_tb_col">' + '<span class="label label-sm black">' + ' odd: ' + tb.odd.toFixed(3) + '</span>' + '</td>' +
                //     '<td class="dc_tb_col">' + '<span class="label label-sm black">' + ' profit: ' + String((tb.total_return-tb.amount).toFixed(1)) + '</span>' + '</td>' +
                //     '<td class="dc_tb_col">' + '<span class="label label-sm black">' + tb.bookmaker_name + '</span>' + '</td>' +
                //     '<td>' + "<a href='" + tb_url + "' class='pjax_call url_param_dependent'" + ">" + 'details' + "</a>" + '</td>' +
                //     '</tr>' + '</tbody>' + '</table>';
                var tb_text =
                    '<table class="table table-condensed parent_tb">' + '<tbody>' + '<tr>' +
                    '<td style="float: left">' + "<a href='" + tb_url + "' class='pjax_call url_param_dependent'>" + '<span class="label label-sm tb_group_status ' + color_class + ' ">' + tb.status + '</span>' + "</a>" + '</td>' +
                    '<td style="float: left">' + "<a href='" + tb_url + "' class='pjax_call url_param_dependent'" + ">" + 'details' + "</a>" + '</td>' +
                    '</tr>' + '</tbody>' + '</table>';
                var output = '<div class="row bev_dc_table_group_wrapper">' + '<div class="col-xs-6">' + tb_text + '</div>' + '</div>';
                // IMPORTANT:
                // groups are sorted automatically from their text, so I add a group sorting text in the start
                // of each group text so that they are sorted by it. It is the tb_id formatted as 09d (79->'000000079')
                // todo order them by date
                var group_sorting_text = '<div class="hidden">' + fmt(d.total_bet_id) + '</div>';
                return group_sorting_text + output;
                // return fmt(d.total_bet_id) + 'sth'
            })
            .order(d3.descending)
            .size(Infinity) // (_optional_) max number of records to be shown, `default = 25`
            // Important: you have to define the order of groups (d.total_bet_id) and of dimension
            .sortBy(function (d) {return d.event_date;})
            .showGroups(true)
            // There are several ways to specify the columns; see the data-table documentation.
            // This code demonstrates generating the column header automatically based on the columns.
            .columns([
                {label:'', format:function(d){return '';}},
                {
                    label: 'Event',
                    format: function(d){
                        return '<span class="label label-sm label-info label_zak_d1">' + d.home_team + ' - ' + d.away_team + '</span>';
                    }
                },
                {
                    label: 'Choice',
                    format: function(d){return '<span class="label label-sm label-info label_zak_l1">' + d.choice + '</span>';}
                },
                {
                    label: 'Market',
                    format: function(d){return d.market_type;}
                },
                {
                    label: 'Odd',
                    format: function(d){return d.selected_odd;}
                },
                {
                    label: 'Date',
                    format: function(d) {
                        var format = d3.format('02d');
                        var event_date = Moment(d.event_date).format(date_format);
                        return event_date
                    }
                },
                {
                    label: 'Competition',
                    format: function(d){
                        return d.competition_generic_name + ' ' + d.season;
                    }
                },
                {
                    label: 'Result',
                    format: function(d) {
                        if (d.home_goals != 'None' && d.away_goals != 'None') {
                            return d.home_goals + '-' + d.away_goals
                        } else {
                            return '-'
                        }
                    }
                },
                {
                    label: 'Status',
                    format: function(d){
                        return '<span class="label label-sm bev_status">' + d.selection_status + '</span>';
                    }
                }
                //{
                //    label: 'Stats',
                //    format: function(d){
                //        var tb_url = urls.stats.bet_event_detail + d.bet_event_id + "/";
                //        var bev_link = "<a href='" + tb_url + "' class='pjax_call'>" + 'stats' + "</a>";
                //        return bev_link;
                //    }
                //}
            ])
            // (_optional_) custom renderlet to post-process chart using [D3](http://d3js.org)
            .on('renderlet', function (table) {
                //table.selectAll('.dc-table-group').classed(void_class, true);
                //table.selectAll('.dc-table-group').each(function(d){
                //    console.log("tb d", d)
                //});

                table.selectAll('.dc-table-row').each(function(d){
                    // d are the data object
                    $(this).find('td._1').addClass('bg_zak_dark');
                    $(this).find('td._2').addClass('bg_zak_orange');

                    if(d.selection_status === won_str){ $(this).find('td._8').find('span').addClass('won')}
                    else if(d.selection_status === lost_str){ $(this).find('td._8').find('span').addClass('lost')}
                    else if(d.selection_status === void_str){ $(this).find('td._8').find('span').addClass('label-default')}
                    else{$(this).find('td._8').find('span').addClass('label-primary')}
                    //d.status === won_str ? d3.select(this).classed('row_won', true) : d3.select(this).classed('row_lost', true);
                });
                update_pagination();
            });

        var ofs = 0, pag = 20;
        // slicing applies on the dimension (bevs) not the tbs. There is no way to find how many groups are sliced?
        // for example when it shows the maximum allowed number of bevs (40 here) how many groups it shows?
        // If you don't know this, then you can't show the number of displayed tbs
        function display(selected_tbs_num, selected_bevs_num, end) {
            //d3.select('#bev_dc_table_num_top')
            //  .text(Math.min(pag-ofs, end));
            d3.select('#size_top').text(selected_tbs_num);
              //d3.select('#begin_top')
              //    .text(ofs);
              //d3.select('#end_top')
              //    .text(end);
              d3.select('#bev_dc_table_last_top')
                  .attr('disabled', ofs-pag<0 ? 'true' : null);
              d3.select('#bev_dc_table_next_top')
                  .attr('disabled', ofs+pag>=selected_bevs_num ? 'true' : null);

                //d3.select('#bev_dc_table_num_bottom')
                //  .text(pag-ofs);
                d3.select('#size_bottom').text(selected_tbs_num);
              //d3.select('#begin_bottom')
              //    .text(ofs);
              //d3.select('#end_bottom')
              //    .text(end);
              d3.select('#bev_dc_table_last_bottom')
                  .attr('disabled', ofs-pag<0 ? 'true' : null);
              d3.select('#bev_dc_table_next_bottom')
                  .attr('disabled', ofs+pag>=selected_bevs_num ? 'true' : null);
        }
        update_pagination = function update() {
            var selected_tbs_num = tb_ids_dim.top(Infinity).length;
            var selected_bevs_num = event_date_dim.top(Infinity).length;
            var end = Math.min(ofs+pag, selected_bevs_num);
            if (selected_bevs_num < ofs && ofs !== 0){
                // if you have pressed next and you see slice 41-80, then you make another filtering and the selected
                // bevs are less than 40, then you must switch to the first page in order to show the bevs
                show_first_page();
            }
          bev_table.beginSlice(ofs);
          bev_table.endSlice(ofs+pag);
          display(selected_tbs_num, selected_bevs_num, end);
        };
        next = function next() {
          ofs += pag+1;
          update_pagination();
          bev_table.redraw();
        };
        last = function last() {
          ofs -= pag+1;
          update_pagination();
          bev_table.redraw();
        };
        show_first_page = function first(){
            ofs = 0;
            update_pagination();
            bev_table.redraw();
        };

        return bev_table
    };

    //function tbs_table(event_date_dim, bev_table){
    //    // the problem with this approach is that the bev charts (the pies) that do not filter the tbs crossfilter
    //    // don't affect this table (since it is based on the tbs crossfilter).
    //    bev_table
    //        .dimension(event_date_dim)
    //        // Data table does not use crossfilter group but rather a closure as a grouping function
    //        .group(function (d) {return 'common group'})
    //        .order(d3.descending)
    //        .size(15) // (_optional_) max number of records to be shown, `default = 25`
    //        .sortBy(function (d) {return d.date;})
    //        .showGroups(false)
    //        // There are several ways to specify the columns; see the data-table documentation.
    //        // This code demonstrates generating the column header automatically based on the columns.
    //        .columns([
    //            {
    //                label: 'Date',
    //                format: function(d) {
    //                    var format = d3.format('02d');
    //                    var event_date = Moment(d.date).format(date_format);
    //                    return event_date
    //                }
    //            },
    //            {
    //                label: 'Events',
    //                format: function(d){
    //                    var html_elems = '';
    //                    for (var i=0; i< d.home_teams.length; i++){
    //                        html_elems += '<span class="label label-sm label-info label_zak_d1">' + d.home_teams[i] + ' - ' + d.away_teams[i] + '</span>';
    //                    }
    //                    return '<div class="label label-sm label-info label_zak_d1">' + html_elems + '</div>';
    //                }
    //            },
    //            {
    //                label: 'Choice',
    //                format: function(d){
    //                    var html_elems = '';
    //                    for (var i=0; i< d.home_teams.length; i++){
    //                        html_elems += '<span class="label label-sm label-info label_zak_l1">' + d.bet_event_choices[i] + '</span>';
    //                    }
    //                    return '<div class="label label-sm label-info label_zak_l1">' + html_elems + '</div>';
    //                }
    //            },
    //            {
    //                label: 'Market',
    //                format: function(d){
    //                    var html_elems = '';
    //                    for (var i=0; i< d.home_teams.length; i++){
    //                        html_elems += '<span class="">' + d.markets[i] + '</span>';
    //                    }
    //                    return '<div class="">' + html_elems + '</div>';
    //                }
    //            },
    //            {
    //                label: 'Status',
    //                format: function(d){return d.status}
    //            },
    //            {
    //                label: 'Odd',
    //                format: function(d){return d.odd;}
    //            },
    //            {
    //                label: 'Competition',
    //                format: function(d){
    //                    var html_elems = '';
    //                    for (var i=0; i< d.home_teams.length; i++){
    //                        html_elems += '<span class="">' + d.competitions[i] + '</span>';
    //                    }
    //                    return '<div class="">' + html_elems + '</div>';
    //                }
    //            },
    //            //{
    //            //    label: 'Result',
    //            //    format: function(d) {
    //            //        if (d.home_goals != 'None' && d.away_goals != 'None') {
    //            //            return d.home_goals + '-' + d.away_goals
    //            //        } else {
    //            //            return '-'
    //            //        }
    //            //    }
    //            //},
    //            {
    //                label: 'Event Status',
    //                format: function(d){
    //                    var html_elems = '';
    //                    for (var i=0; i< d.home_teams.length; i++){
    //                        html_elems += '<span class="">' + d.bet_event_statuses[i] + '</span>';
    //                    }
    //                    return '<div class="">' + html_elems + '</div>';
    //                }
    //            }
    //            //{
    //            //    label: 'Stats',
    //            //    format: function(d){
    //            //        var tb_url = urls.stats.bet_event_detail + d.bet_event_id + "/";
    //            //        var bev_link = "<a href='" + tb_url + "' class='pjax_call'>" + 'stats' + "</a>";
    //            //        return bev_link;
    //            //    }
    //            //}
    //        ])
    //
    //        // (_optional_) custom renderlet to post-process chart using [D3](http://d3js.org)
    //        .on('renderlet', function (table) {
    //            //table.selectAll('.dc-table-group').classed(void_class, true);
    //            //table.selectAll('.dc-table-group').each(function(d){
    //            //    console.log("tb d", d)
    //            //});
    //
    //
    //            table.selectAll('.dc-table-row').each(function(d){
    //                // d are the data object
    //                $(this).find('td._1').addClass('bg_zak_dark');
    //                $(this).find('td._2').addClass('bg_zak_orange');
    //
    //                if(d.status === won_str){ $(this).find('td._4').find('span').addClass('won')}
    //                else if(d.status === lost_str){ $(this).find('td._4').find('span').addClass('lost')}
    //                else if(d.status === void_str){ $(this).find('td._4').find('span').addClass('label-default')}
    //                //d.status === won_str ? d3.select(this).classed('row_won', true) : d3.select(this).classed('row_lost', true);
    //            });
    //        });
    //
    //    return bev_table
    //}

    return {
        bind_events: bind_events,
        bet_events_market_pie: bet_events_market_pie,
        bet_events_choice_pie: bet_events_choice_pie,
        bet_events_status_pie: bet_events_status_pie,
        bev_table: bet_events_table
    }
});
