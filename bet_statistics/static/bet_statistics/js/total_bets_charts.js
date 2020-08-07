/**
 * Created by xene on 4/27/2016.
 */

define([
    'jquery',
    'd3',
    'crossfilter',
    'dc',
    'js/libs/colorbrewer',
    'js/utils',
    'js/urls',
    'select2',
    'blockui'
], function($, d3, crossfilter, dc, colorbrewer, Utils, Urls, Select2){

    var config = {
        debug: Utils.config.logger.bet_statistics,
        tb_status_lost: "Lost",
        tb_status_won: "Won",
        x_axis_extremes_col: 'date',
        month_names: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ],
        day_names: ['Mon', 'Tue', 'Wen', 'Thu', 'Fri', 'Sat', 'Sun'],
        colors: {
            // win: d3.rgb("#008000").brighter(0.5),
            // loss: d3.rgb("#FF0000").darker(0.3),
            // open: d3.rgb("#3182bd")
            // DARK THEME
            win: d3.rgb("#224c22"),
            loss: d3.rgb("#7b1f1f"),
            open: d3.rgb("#2a5b84")
            //default: d3.rgb("#3182bd"),
            //orange: d3.rgb("#fd8d3c").brighter(0.2),
            //customRange01: ['#ca0020','#fd8d3c','#92c5de','#404040'],
            //customRange02: ["#230500", "#870800", "#AD4A00", "#FF1B00", "#FFC600"] //colorbrewer.RdGy[9]
        },
        bank_growth_number_span: "#bank_growth_number",
        num_bets_span: "#numbets_number",
        balance_number_span: "#balance_number",
        roi_number_span: "#roi_number",
        real_roi_number_span: "#real_roi_number",
        yield_number_span: "#yield_number",
        average_profit_number_span: "#median_profit",
        chart_ids: ["#status_pie", "#time_bar_chart", "#bank_growth_history_bar_chart", "#deposit_bar_chart",
            "#seasons_bubble_chart", "#stakes_history_bar_chart", "#countries_dc_select", "#competitions_dc_select",
            "#seasons_dc_select", "#home_teams_dc_select", "#away_teams_dc_select", "#bevs_num_dc_select"],
        pie_width: 300,
        pie_height: 170,
        chart_width: 350,
        chart_height: 200,
        min_width_pie: 100,
        max_width_pie: 200
    };

    var log = Utils.create_logger(config.debug);
    var tb_status_lost = config.tb_status_lost;
    var tb_status_won = config.tb_status_won;
    var tb_win_color = config.colors.win;
    var tb_loss_color = config.colors.loss;
    var tb_open_color = config.colors.open;
    var month_names = config.month_names;
    var day_names = config.day_names;
    var urls = Urls;
    var bank_growth_number_span = config.bank_growth_number_span;
    var roi_number_span = config.roi_number_span;
    var real_roi_number_span = config.real_roi_number_span;
    var yield_number_span = config.yield_number_span;
    var average_profit_number_span = config.average_profit_number_span;
    var balance_number_span = config.balance_number_span;
    var x_axis_extremes_col = config.x_axis_extremes_col;
    var chart_ids = config.chart_ids;
    var charts = {};

    function bind_events(){
        $(document).on('click', 'a.reset-all', function(e){
            e.preventDefault();
            dc.filterAll();
            dc.renderAll();
        });

        //for (var i=0; i<chart_ids.length; i++){
        //    if (i==0 || i==1 || i==5){
        //        $(document).on('click', chart_ids[i] + ' a.reset', function(e){
        //            e.preventDefault();
        //            console.debug(i, chart_ids[i]);
        //            charts[chart_ids[i]].filterAll();
        //            dc.redrawAll();
        //        });
        //    }
        //}
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
        $(document).on('click', chart_ids[5] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[5]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[6] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[6]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[7] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[7]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[8] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[8]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[9] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[9]].filterAll();
            dc.redrawAll();
        });
        $(document).on('click', chart_ids[10] + ' a.reset', function(e){
            e.preventDefault();
            charts[chart_ids[10]].filterAll();
            dc.redrawAll();
        });

    }

    function bet_tag_filtering(filtered_tag_names, bet_tags_dim){
        bet_tags_dim.filterFunction(function(d){
            if ($.inArray(d, filtered_tag_names) != -1){
                log('returned d:', d);
                return true
            }
        });

        var filtered_names = bet_tags_dim.top(Infinity);
        var filtered_tb_ids = {};
        log('filtered bet_tags_dim length:', filtered_names.length);
        for (var i=0; i<filtered_names.length; i++){
            if (filtered_names[i]) {
                var tb_entry = filtered_names[i];
                log(i, ': tb_entry', tb_entry['total_bet_id']);
                filtered_tb_ids[tb_entry['total_bet_id']] = tb_entry['total_bet_id'];
            }
        }
        log(filtered_tb_ids)
    }


    function calculate_cumsum_array(action, value, idx, cumsum_array){
        // creates and recalculates the cumsum array by removing/adding to the array from which the cumsum array is calculated
        // value is added to the idx index of the array. Based on this the cumsum is recalculated. For example if a value
        // is added in the middle of the array then this value is added to all the cumsum values greater than the value's index
        var max_idx = cumsum_array.length - 1;
        if (action === 'add'){
            var new_cumsum_value;
            if (idx === 0){ new_cumsum_value = value }else{ new_cumsum_value = cumsum_array[idx-1] + value; }
            cumsum_array.splice(idx, 0, new_cumsum_value);
            var new_max_idx = max_idx+1; // the array size has been increased by 1
            if (idx < new_max_idx) {
                for (var i = idx+1; i <= new_max_idx; i++) {
                    cumsum_array[i] += value;
                }
            }
        }else{
            if (idx < max_idx) {
                for (var j = idx + 1; j <= max_idx; j++) {
                    cumsum_array[j] -= value;
                }
            }
            cumsum_array.splice(idx, 1);
        }
        return cumsum_array
    }

    function calculate_investment_array(cumsum_amounts, cumsum_total_returns){
        // the max value of the calculated array is the current total bet deposits
        var max_idx = cumsum_amounts.length-1;
        var investment_array = [];
        for (var i=0; i<=max_idx; i++){
            if(i === 0){investment_array[i] = cumsum_amounts[0]}else{
                investment_array[i] = cumsum_amounts[i] - (cumsum_total_returns[i-1]);
            }
        }
        return investment_array
    }

    function median(values) {
        var copy = values.slice();
        copy.sort(function (a, b) {
            return a - b;
        });
        var half = Math.floor(copy.length / 2);
        if (copy.length % 2) {
            return copy[half];
        }else{
            return (copy[half-1] + copy[half]) / 2.0;
        }
    }

    function average(values){
        var total = 0;
        for(var i = 0; i < values.length; i++) {
            total += values[i];
        }
        return total / values.length;
    }

    function frequent_value(values){
        var frequency = {};  // array of frequency.
        var max = 0;  // holds the max frequency.
        var result = 0;   // holds the max frequency element.
        for(var v=0; v<values.length; v++) {
            frequency[values[v]]=(frequency[values[v]] || 0)+1; // increment frequency.
            if(frequency[values[v]] > max) { // is this frequency > max so far ?
                    max = frequency[values[v]];  // update max.
                    result = values[v];          // update result.
            }
        }
        return [result, max]
    }

    function describe_cumsum_tag_obj(cumsum_tag_deposits_per_tag){
        // cumsum_tag_deposits_per_tag is an object the attributes of which are the tag_names of the
        // filtered total_bets. Each attribute is an array of the tag deposits cumsum ammount.
        // This way we collect in this object the cumsum deposits for each of the bet tags.
        // The max entry of these arrays are the total deposits made for the respective tag.
        // Then we add the total deposits of all the tags and we get the total deposits amount.

        // The real investment that the user has made is the maximum value between the total deposits amount
        // and the bet deposits amount (which is the max if the investment column).
        // The real investment amount can be used to calculate the deposits roi.
        //
        // * If we filter only a specific tag, the values of the array of the other tags would become 0 due to the
        // remove operation and the total deposit amount will be the total deposit of this tag.
        // So this is a generic way to calculate the deposits roi for any total bets filtering.
        //
        // * Notice: the tbs data has one deposit column for each tag. Let's say tb[0] is tag1 and tb[1] tag2.
        // When the tb[1] is added (or removed) the tag2 deposits array will be fill. But since the tb[1] is
        // in index 1, the first entry of the tag2 deposits array (index 0) will be 0 as it was defined in the server.
        // Similarly all tag deposits arrays will have 0 values in the indexes of tbs with other tags.
        var sum_of_deposits = 0;
        var deposits_per_tag = {};
        for (var bet_tag_name in cumsum_tag_deposits_per_tag) {
            if (cumsum_tag_deposits_per_tag.hasOwnProperty(bet_tag_name)) {
                // We must pick the max of the array (instead of the last entry) beacuse the last entry can be 0
                // since the arrays are static and the last tb can be of another tag
                deposits_per_tag[bet_tag_name] = Math.max.apply(null, cumsum_tag_deposits_per_tag[bet_tag_name]);
                sum_of_deposits += deposits_per_tag[bet_tag_name]
            }
        }
        return [deposits_per_tag, sum_of_deposits]
    }

    function replace_value_of_cumsum_array(cumsum_array, idx){
        // it doesn't remove the entry. It replaces it with 0. The array length stays intact.
        // it's cumsum array so values for bigger indexes are also modified
        //console.log('removing value with idx: ', idx);
        var max_idx = cumsum_array.length - 1;
        if (idx <= max_idx) {
            for (var j = idx; j <= max_idx; j++) {
                // for j = idx the value becomes 0
                cumsum_array[j] -= cumsum_array[idx];
            }
        }
        return cumsum_array
    }

    function append_to_obj_attr(obj_attr, value, idx, num_total_bets){
        // obj_attr is the tag deposits array and it is static. It's length isn't modified by the add/remove operations
        // obj_attr must be defined as an array if it doesn't exist yet. Obj is prepopulated with zeros
        if (! obj_attr){
            obj_attr = Array.apply(null, Array(num_total_bets)).map(Number.prototype.valueOf, 0);
        }
        obj_attr[idx] = value;
        return obj_attr
    }

    function stats_reduce_functions(extra, num_total_bets){
        // calculates these stats for a specific number of total_bets. The stats are aggregated values for a number of total bets.
        // So if you want to calculate the stats for all total bets then your dimension will be one that returns all individual total_bets
        // and you will use the groupAll to create one group and use the reduce functions to that group to get the stats for this group.
        // Otherwise you have to use a dimension that creates groups of individual total bets and apply the reduce functions
        // to those groups. You will get the stats for each group.
        function reduceAdd(p,v){
            // The order of all the p arrays is reflected by the counters order. This means that the
            // index of any entry of an array is the same with the index of its counter in the counters array
            //console.log('p:  ' + p);
            ++p.count;
            p.amount += v.amount; //cumsum
            p.total_return += v.total_return; //cumsum
            p.bank_growth = p.total_return - p.amount;
            p.lost_stakes = v.status === tb_status_lost ? p.lost_stakes + v.amount : p.lost_stakes;
            p.pure_wins = v.status === tb_status_won ? p.pure_wins + (v.total_return - v.amount) : p.pure_wins;
            //p.net_profit = p.pure_wins - p.lost_stakes; // this is a second calculation for the same thing
            p.net_profit = p.bank_growth;
            p.yield = p.amount === 0 ? 0 : (p.net_profit/p.amount)*100;
            //p.bet_deposits += v.deposit;
            //if (p.bet_deposits === 0){p.bet_deposits = p.cumsum_amounts[0]}
            var vidx = v_idx(p, v);
            //log('max index:' + (p.counters.length-1) + ' added counter index:' + vidx + ' counter:' + v.counter);
            p.counters.splice(vidx, 0, v.counter);

            var static_vidx = static_v_idx(p, v);
            if (p.static_counters.length != num_total_bets){
                p.static_counters.splice(static_vidx, 0, v.counter);
            }

            //p.cumsum_amounts = calculate_cumsum_array('add', v.amount, vidx, p.cumsum_amounts);
            //p.cumsum_total_returns = calculate_cumsum_array('add', v.total_return, vidx, p.cumsum_total_returns);
            p.cumsum_amounts = 0;
            p.cumsum_total_returns = 0;
            //// Unfortunately the investment array is recalculated in every iteration
            //// investment_array is used only for bet_deposits calculations which are not to be used
            //p.investment_array = calculate_investment_array(p.cumsum_amounts, p.cumsum_total_returns);
            //p.bet_deposits = Math.max.apply(null, p.investment_array);
            //p.bets_roi = (p.net_profit/p.bet_deposits)*100;
            p.bet_deposits = 0;
            p.bets_roi = 0;

            var current_tag = v.bet_tag_name;
            //console.log("current tag, vidx: ", current_tag, vidx);

            // Important: the name of the deposit and withdrawal columns (tag_name_deposit and tag_name_withdrawal) are defined in the server.
            var bet_group_deposit_col_name = current_tag + '_deposit_cumsum';
            p.cumsum_tag_deposits_per_tag[current_tag] = append_to_obj_attr(p.cumsum_tag_deposits_per_tag[current_tag], v[bet_group_deposit_col_name], static_vidx, num_total_bets);
            var dep_res = describe_cumsum_tag_obj(p.cumsum_tag_deposits_per_tag);

            var bet_group_withdrawal_col_name = current_tag + '_withdrawal_cumsum';
            p.cumsum_tag_withdrawals_per_tag[current_tag] = append_to_obj_attr(p.cumsum_tag_withdrawals_per_tag[current_tag], v[bet_group_withdrawal_col_name], static_vidx, num_total_bets);
            var withdr_res = describe_cumsum_tag_obj(p.cumsum_tag_withdrawals_per_tag);

            p.sum_of_deposits = dep_res[1];
            p.sum_of_withdrawals = withdr_res[1];
            p.real_investment = Math.max(p.bet_deposits, p.sum_of_deposits);
            //p.deposits_roi = (p.net_profit/p.real_investment)*100;
            p.real_investment? p.deposits_roi = (p.net_profit/p.real_investment)*100 : p.deposits_roi = 0;

            if (extra) {
                p.amounts.splice(vidx, 0, v.amount);
                p.max_amount = Math.max.apply(null, p.amounts);
                p.median_amount = average(p.amounts);
                p.profits.splice(vidx, 0, v.total_return - v.amount);
                var max_profit = Math.max.apply(null, p.profits);
                max_profit >= 0 ? p.max_profit = max_profit || 0 : p.max_profit = 0;
                p.median_profit = average(p.profits);
                p.odds.splice(vidx, 0, v.odd);
                p.max_odd = Math.max.apply(null, p.odds);
                p.median_odd = average(p.odds);
                var teams = v.home_teams;
                teams.concat(v.away_teams);
                var attrs = ['teams', 'competitions', 'markets'];
                for (var i = 0; i < attrs.length; i++) {
                    var attr = attrs[i];
                    var v_attr = v[attr];
                    if (attr === 'teams') {v_attr = teams;}
                    for (var j = 0; j < v_attr.length; j++) {
                        var v_child = v_attr[j];
                        p[attr].push(v_child);
                    }
                }
                p.bookmakers.push(v.bookmaker_name);

                p.pop_team = frequent_value(p.teams)[0];
                p.pop_competition = frequent_value(p.competitions)[0];
                p.pop_market = frequent_value(p.markets)[0];
                p.pop_bookmaker = frequent_value(p.bookmakers)[0];
            }

            return p
        }
        function reduceRemove (p,v){
            --p.count;
            p.amount -= v.amount;
            p.total_return -= v.total_return;
            p.bank_growth = p.count ? p.total_return - p.amount : 0;
            p.lost_stakes = v.status === tb_status_lost ? p.lost_stakes - v.amount : p.lost_stakes;
            p.pure_wins = v.status === tb_status_won ? p.pure_wins - (v.total_return - v.amount) : p.pure_wins;
            //p.net_profit = p.pure_wins - p.lost_stakes;
            p.net_profit = p.bank_growth;
            p.yield = p.amount === 0 ? 0 : (p.net_profit/p.amount)*100;

            var vidx = p.counters.indexOf(v.counter); // counters is already sorted
            var static_vidx = p.static_counters.indexOf(v.counter); // static_counters has fixed length
            //log('max index:' + (p.counters.length-1) + ' removed counter index:' + vidx + ' counter:' + v.counter);
            p.counters.splice(vidx, 1);
            //p.cumsum_amounts = calculate_cumsum_array('remove', v.amount, vidx, p.cumsum_amounts);
            //p.cumsum_total_returns = calculate_cumsum_array('remove', v.total_return, vidx, p.cumsum_total_returns);
            p.cumsum_amounts = 0;
            p.cumsum_total_returns = 0;
            //// Unfortunately the investment array is recalculated in every iteration
            //p.investment_array = calculate_investment_array(p.cumsum_amounts, p.cumsum_total_returns);
            //p.investment_array.length ? p.bet_deposits = Math.max.apply(null, p.investment_array) : p.bet_deposits = 0;
            //p.bet_deposits ? p.bets_roi = (p.net_profit/p.bet_deposits)*100 : p.bets_roi = 0;
            p.bet_deposits = 0;
            p.bets_roi = 0;

            var current_tag = v.bet_tag_name;

            p.cumsum_tag_deposits_per_tag[current_tag] = replace_value_of_cumsum_array(p.cumsum_tag_deposits_per_tag[current_tag], static_vidx);
            var dep_res = describe_cumsum_tag_obj(p.cumsum_tag_deposits_per_tag);

            p.cumsum_tag_withdrawals_per_tag[current_tag] = replace_value_of_cumsum_array(p.cumsum_tag_withdrawals_per_tag[current_tag], static_vidx);
            var withdr_res = describe_cumsum_tag_obj(p.cumsum_tag_withdrawals_per_tag);

            dep_res[1] ? p.sum_of_deposits = dep_res[1] : p.sum_of_deposits = 0;
            withdr_res[1] ? p.sum_of_withdrawals = withdr_res[1] : p.sum_of_withdrawals = 0;

            p.real_investment = Math.max(p.bet_deposits, p.sum_of_deposits);
            p.real_investment? p.deposits_roi = (p.net_profit/p.real_investment)*100 : p.deposits_roi = 0;

            if (extra) {
                p.amounts.splice(vidx, 1);
                p.amounts.length ? p.max_amount = Math.max.apply(null, p.amounts) : p.max_amount = 0;
                p.median_amount = average(p.amounts) || 0;
                p.profits.splice(vidx, 1);
                var max_profit = Math.max.apply(null, p.profits);
                max_profit >= 0 ? p.max_profit = max_profit || 0 : p.max_profit = 0;
                p.median_profit = average(p.profits) || 0;
                p.odds.splice(vidx, 1);
                p.odds.length ? p.max_odd = Math.max.apply(null, p.odds) : p.max_odd = 0;
                p.median_odd = average(p.odds) || 0;
                var teams = v.home_teams;
                teams.concat(v.away_teams);
                var attrs = ['teams', 'competitions', 'markets'];
                for (var i = 0; i < attrs.length; i++) {
                    var attr = attrs[i];
                    var v_attr = v[attr];
                    if (attr === 'teams') {v_attr = teams;}
                    for (var j = 0; j < v_attr.length; j++) {
                        var v_child = v_attr[j];
                        var idx = p[attr].indexOf(v_child);
                        if (idx != -1) { p[attr].splice(idx, 1) }
                    }
                }
                p.bookmakers.splice(vidx, 1);

                p.pop_team = frequent_value(p.teams)[0];
                p.pop_competition = frequent_value(p.competitions)[0];
                p.pop_market = frequent_value(p.markets)[0];
                p.pop_bookmaker = frequent_value(p.bookmakers)[0];
            }
            return p
        }
        function reduceInitial(){
            var obj = {
                counters: [],
                static_counters: [],
                cumsum_amounts: [],
                cumsum_total_returns: [],
                investment_array: [],
                count: 0,
                amount: 0,
                total_return: 0,
                bank_growth: 0,
                lost_stakes: 0,
                pure_wins: 0,
                net_profit: 0,
                yield: 0,
                bet_deposits: 0,
                bets_roi: 0,
                cumsum_tag_deposits_per_tag: {},
                cumsum_tag_withdrawals_per_tag: {},
                sum_of_deposits: 0,
                sum_of_withdrawals: 0,
                real_investment: 0,
                deposits_roi: 0
            };
            if (extra){
                obj.amounts = [];
                obj.max_amount = 0;
                obj.median_amount = 0;
                obj.profits = [];
                obj.max_profit = 0;
                obj.median_profit = 0;
                obj.odds = [];
                obj.max_odd = 0;
                obj.median_odd = 0;
                obj.teams = [];
                obj.pop_team = '';
                obj.competitions = [];
                obj.pop_competition = '';
                obj.markets = [];
                obj.pop_market = '';
                obj.bookmakers = [];
                obj.pop_bookmaker = '';
            }
            return obj
        }
        return [reduceAdd, reduceRemove, reduceInitial]
    }

    function total_bets_status_pie(status_pie, totalBetStatusDim){
        var byStatus = totalBetStatusDim.group().reduceCount();

        //window.onresize = function() {
        //    // responsive on resizing. Now you have to reload
        //    status_pie
        //      .width(width)
        //      .height(null)
        //      .redraw();
        //};

        // it would be good if I could get the #status_pie id from the status_pie dc chart
        // closest div is the self which is also a div with class "col-..."
        var width = $('#status_pie').closest('div').width();
        width = 0.8*width;
        width = Utils.trim_value(width, config.max_width_pie, config.min_width_pie);
        var inner_radius = width/6;
        status_pie
            //.width(config.pie_width).height(config.pie_height)
            .width(width).height(null)
            .label(function(d) { return d.key +" "+ d.value; })
            .title(function(d){
                var all = 0;
                for (var j=0; j<byStatus.all().length; j++){all += byStatus.all()[j].value;}
                return d.key
                    +"\n"+ d.value + " bets"
                    +' (' + Math.floor(d.value / all * 100) + '%)';
            })
            .dimension(totalBetStatusDim)
            .group(byStatus)
            .innerRadius(inner_radius)
            .colors(d3.scale.ordinal().range([tb_loss_color.toString(), tb_win_color.toString(), tb_open_color.toString()]))
            .colorDomain([0,1,2])
            .colorAccessor(function(d, i){
                if (d.key === tb_status_lost){
                    return 0
                }else if (d.key === tb_status_won){
                    return 1
                }else{ return 2}
            })
            .controlsUseVisibility(true);

        charts[chart_ids[0]] = status_pie;
        return status_pie;
    }

    function calculate_min_max_dates(dimension, value, offset){
        if (dimension.top(Infinity).length){
            var minDate = dimension.bottom(1)[0][value];
            var maxDate = dimension.top(1)[0][value];
            //log("date extremes", minDate, maxDate);
            var numberOfDaysToAdd = offset;
            var calculated_min = new Date(minDate);
            var calculated_max = new Date(maxDate);
            calculated_min.setDate(calculated_min.getDate() - numberOfDaysToAdd);
            calculated_max.setDate(calculated_max.getDate() + numberOfDaysToAdd);
            //console.debug('calculated_min', calculated_min, typeof (calculated_min));
            //console.debug('minDate', minDate, typeof (minDate));
            return [calculated_min, calculated_max]
        }
        return [null, null]
    }

    //patch group

    //function patch_group(group, groups_array){
    //    // we patch the all() method to return an array of {key: date, value: bank_growth} objects. This is done because the all()
    //    // method is used by dc.js and it expects this kind of format. I patch the all() method instead of using a valueAccessor
    //    // in order to apply the post treatment. (I could apply the post treatment to the return of the original all() method
    //    // and use the valueAccessor for the chart, in order not to affect the original return)
    //    group.all = function(){
    //        var new_obj = [];
    //        for (var i=0; i<groups_array.length; i++) {
    //            var obj = groups_array[i];
    //            if (obj.hasOwnProperty('key') && obj.hasOwnProperty('value')) {
    //                if(obj.value.hasOwnProperty('bank_growth')){
    //                    var new_key = obj.key;
    //                    var new_value = obj.value.bank_growth;
    //                    new_obj.push({key: new_key, value: new_value});
    //                }
    //            }
    //        }
    //        // post treatment of the resulted array: Handling of the cases in which all the total bets of a group are removed.
    //        // If all the total bets of this group have been removed (the bank_growth for this particular group is undefined),
    //        // then replace it with the bank_growth of its previous group. If it is the first group the replace it with 0.
    //        // * Have in mind that the brush has a meaning when you start from the beginning and have an arbitrary end. It shows
    //        // you the bank_growth until that moment. If you change the start it isn't as if you have started from that point. To
    //        // do so you had to calculate the bank_growth in js. Now the bank_growth contains the info of the previous total bets.
    //        for (var j=0; j<new_obj.length; j++){
    //            if (j==0 && new_obj[j].value == undefined){
    //                new_obj[j].value = 0;
    //            }else if(new_obj[j].value == undefined){
    //                new_obj[j].value = new_obj[j-1].value;
    //            }
    //        }
    //        //log('new obj after post treatment', new_obj);
    //        return new_obj
    //    }
    //}

    function v_idx(p, v){
        // find the index of v inside p array based on its counter value. The index will be used to insert v.counter to the
        // counters array in the proper index, so counters array will always be sorted. This way the index of a v-value
        // in a p-array-of-values is the index of its v-counter in the p-counters array. So we can use this to add/remove
        // the proper v-value
        var bisect = crossfilter.bisect.by(function(d) { return d; }).left; // get the index
        return bisect(p.counters, v.counter, 0, p.counters.length); // of counters array
    }

    function static_v_idx(p, v){
        var bisect = crossfilter.bisect.by(function(d) { return d; }).left; // get the index
        return bisect(p.static_counters, v.counter, 0, p.static_counters.length); // of counters array
    }

    function bank_growth_history_chart(bank_growth_history_chart, date_dim, time_bar_chart){
        // TODO sync bank_growth chart with time. I need to recalculate the bank_growth based on the bank_growth values from server
        // To sync I need to activate the rangeChart and the path group function. Have in mind that I need the cumsum amount and total_return from
        // the server because each group value must be added to the previous group value. So one way to have this value
        // is to have it from the server. I could return the cumsum amount and total return instead of investment for example.

        // * With this set of reduce functions and patched group.all() method, we can add and remove total bets arbitrarily
        // * (not only from the beginning or the end of a group). The current bank_growth will always be the correct one.
        function reduceAdd(p, v) {
            var vidx = v_idx(p,v);
            p.counters.splice(vidx, 0, v.counter);
            // use this index to add it to the values array. The group's bank_growth will be the bank_growth value of the latest record
            // which is the record with the biggest counter
            var bank_growth_per_id = {total_bet_id : v.total_bet_id, current_bank_growth: v.bank_growth};
            p.values.splice(vidx, 0, bank_growth_per_id);
            p.bank_growth = p.values[p.values.length - 1].current_bank_growth;

            //console.debug('p.bank_growth', p.bank_growth, 'vidx', vidx, 'v.counter', v.counter, 'p.counters[vidx]', p.counters[vidx], ' bank_growth_array=', p.bank_growth_array);
            // in case of empty bets: (if the first is empty then it stays null)
            // p.bank_growth_array.splice(v.counter-1, 0, p.bank_growth);
            //if (!p.bank_growth && v.counter != 1){
            //    console.debug('changing bank, bank_growth_array=', p.bank_growth_array);
            //    p.bank_growth = p.bank_growth_array[p.bank_growth_array.length-1];
            //    console.debug('new bank growth', p.bank_growth);
            //    //p.bank_growth_array.splice(v.counter-1, 0, p.bank_growth);  // so that it doesn't stay as null in the array
            //    //    and it can be used if the next bet is null
            //}
            //p.bank_growth_array.splice(v.counter-1, 0, p.bank_growth);
            //console.debug('p.bank_growth_array', p.bank_growth_array);

            return p;
        }
        function reduceRemove(p, v) {
            var index = p.counters.indexOf(v.counter);
            if (index > -1) {
                p.counters.splice(index, 1);
                //p.bank_growth_array.splice(index, 1);
            }
            // I remove from the values array the object that has been selected to be removed.
            // The objects that don't pass the test are removed.
            p.values = p.values.filter(function( bank_growth_per_id ) {
                return bank_growth_per_id.total_bet_id != v.total_bet_id;
            });

            // If ALL the total bets of a particular group are removed then bank_growth is set to undefined.
            // This will be treated later with post treatment in the patched group.all method
            if(p.values.length === 0) {
                p.bank_growth = undefined;
                return p;
            }

            p.bank_growth = p.values[p.values.length - 1].current_bank_growth;
            return p;
        }
        function reduceInitial() {
          // counters will be an array of total bets' counter values. It is used to determine the index of a total bet
          // values will be an array of {total_bet_id : v.total_bet_id, current_bank_growth: v.bank_growth} objects
          return { counters: [], values: [], bank_growth: 0, bank_growth_array: [] };
        }

        var by_date_bank_growth = date_dim.group().reduce(reduceAdd, reduceRemove, reduceInitial);
        //var groups_array = by_date_bank_growth.all();
        //patch_group(by_date_bank_growth, groups_array);
        var num_groups = by_date_bank_growth.size();

        var fake_by_date_group = remove_null_bins(by_date_bank_growth);

        var date_extremes = calculate_min_max_dates(date_dim, x_axis_extremes_col, 2);
        var minDate = date_extremes[0];
        var maxDate = date_extremes[1];
        var fmt = d3.format('.1f');

        bank_growth_history_chart
            // fitting to the parent div if width or height is set to null
            .width(null)
            .height(null)
            //.margins({top: 0, right: 50, bottom: 20, left: 40})
            .x(d3.time.scale().domain([minDate,maxDate]))
            .xUnits(d3.time.days)
            //.xAxisPaddingUnit(d3.time.day)
            //.xAxisPadding("2")
            .renderArea(true)
            .yAxisLabel("")  // just for adding the default padding so that the y axis numbers are shown
            //.elasticY(true)
            .yAxisPadding("20%")
            .renderHorizontalGridLines(true)
            //.dotRadius(5)
            .brushOn(false)
            //.rangeChart(time_bar_chart)
            //.mouseZoomable(true)
            .title(function(d){
                var dateFormat = d3.time.format("%d-%m-%Y");
                return dateFormat(d.key)
                    +"\nBank Growth: "+ fmt(d.value.bank_growth);
            })
            .valueAccessor(function(p){return p.value.bank_growth})
            .dimension(date_dim)
            .group(fake_by_date_group, "bank_growth")

            .on('renderlet', function(chart) {
                // horizontal line on y = 0
                var left_y = 0, right_y = 0;
                var extra_data = [{x: chart.x().range()[0], y: chart.y()(left_y)}, {x: chart.x().range()[1], y: chart.y()(right_y)}];
                var line = d3.svg.line()
                    .x(function(d) { return d.x; })
                    .y(function(d) { return d.y; })
                    .interpolate('linear');
                var chartBody = chart.select('g.chart-body');
                var path = chartBody.selectAll('path.extra').data([extra_data]);
                path.enter().append('path').attr({
                    class: 'extra',
                    stroke: 'black',
                    id: 'extra-line'
                });
                path.attr('d', line)});
            //.xAxis().ticks(num_groups);
            //.xAxis().ticks(4);
        bank_growth_history_chart.yAxis().tickFormat(function(v) {return v.toFixed(0);});
        bank_growth_history_chart.xAxis().ticks(3).tickFormat(function(v){
                var month_idx = v.getMonth();
                return month_names[month_idx] + ' ' + v.getDate();
            });

        // set equal max and min Y axis limits for styling purposes (only works when NOT elasticY)
        var minY = bank_growth_history_chart.yAxisMin();
        var maxY = bank_growth_history_chart.yAxisMax();
        var absMaxY = Math.abs(maxY);
        var absMinY = Math.abs(minY);
        var maxes = Utils.indexOfMax([absMinY, absMaxY]);
        var max_abs_val = maxes[1];
        var range = [-max_abs_val, max_abs_val].sort();
        bank_growth_history_chart.y(d3.scale.linear().domain(range));
        //debugger;
    }

    function time_bar_chart(time_bar_chart, date_dim){
        //var decision_date_dim = total_bets_cf.dimension(function(d){ return d3.time.day(d.decision_date) });
        var tbs_by_day = date_dim.group();

        var date_extremes = calculate_min_max_dates(date_dim, x_axis_extremes_col, 2);
        var minDate = date_extremes[0];
        var maxDate = date_extremes[1];

        //var width = document.getElementById('box-test').offsetWidth;
        time_bar_chart
            .width(null) /* dc.barChart('#monthly-volume-chart', 'chartGroup'); */
            .height(40)
            .margins({top: 0, right: 50, bottom: 20, left: 40})
            .dimension(date_dim)
            .group(tbs_by_day)
            //.yAxisLabel("")
            .centerBar(true)
            .gap(1)
            .x(d3.time.scale().domain([minDate, maxDate]))
            .xUnits(d3.time.days) // the number of data projections on x axis (number of bars for bar chart or number of dots for line chart)
            //.xAxisPaddingUnit(d3.time.day)
            //.xAxisPadding("2")
            .round(d3.time.day.round) //range selection brush will select whole days
            .alwaysUseRounding(true)
            .controlsUseVisibility(true)
            .yAxis().ticks(0);
        time_bar_chart.xAxis().ticks(3).tickFormat(function(v){
                var month_idx = v.getMonth();
                return month_names[month_idx] + ' ' + v.getDate();
            });
        charts[chart_ids[1]] = time_bar_chart;
        return time_bar_chart
    }

    function bank_growth_history_bar_chart(bank_growth_history_bar_chart, total_bets_counter_dim, num_total_bets){
        var by_counter_bank_growth = total_bets_counter_dim.group().reduceSum(function(d){return d.bank_growth});

        var min_x = 0;
        var max_x = 10;

        var width = $('#bank_growth_history_bar_chart').parent().closest('div.portlet-body').width();
        var height = null;

        bank_growth_history_bar_chart
            .width(width)
            .height(height)
            .x(d3.scale.linear().domain([min_x, num_total_bets+1]))
            .yAxisLabel("Bank Growth")
            .centerBar(true)
            .elasticY(true)
            .yAxisPadding("10%")
            .renderHorizontalGridLines(true)
            .dimension(total_bets_counter_dim)
            .group(by_counter_bank_growth)
            .xAxis().ticks(Math.min(num_total_bets, max_x));
        return bank_growth_history_bar_chart;
    }

    function remove_empty_bins(group){
        return {
            all: function(){
                return group.all().filter(function(d){
                    return d.value != 0
                })
            }
        }
    }

    function remove_null_bins(group){
        return {
            all: function(){
                return group.all().filter(function(d){
                    return d.value.bank_growth != null
                })
            }
        }
    }

    function remove_empty_bins_2(group){
        return {
            all: function(){
                return group.all().filter(function(d){
                    return d.value[0] != 0 && d.value[1] != 0
                })
            }
        }
    }

    function select_stack(i) {
        return function(d) {
            return d.value[i];
        };
    }

    function stakes_history_bar_chart(stakes_history_chart, total_bets_counter_dim, num_total_bets){
        var by_counter_stake = total_bets_counter_dim.group().reduceSum(function(d){return d.amount});
        var by_counter_profit = total_bets_counter_dim.group().reduceSum(function(d){
            // if total_return is null (open bet) I return 0. If it is 0 I return 0. It seems that this isn't
            // a problem for the empty bins removal. These bins with this 0 value are not removed. why?
            var profit = 0;
            if (d.total_return != null){
                profit = d.total_return != 0 ? d.total_return - d.amount : 0;
            }
            return profit
        });

        var min_x = 0;
        var max_x = 10;

        var width = $('#stakes_history_bar_chart').parent().closest('div.portlet-body').width();

        var fake_stake_group = remove_empty_bins(by_counter_stake);
        var fake_profit_group = remove_empty_bins(by_counter_profit);
        var combined_group = Utils.combine_groups(fake_stake_group, fake_profit_group);

        var original_method = combined_group.all;
        combined_group.all = function(){
            // patching the all method to return the keys as integers not as strings, so that they
            // are ordered correctly in the charts X axis
            var res = original_method.apply(this, arguments);
            for (var i=0; i<res.length; i++){
                res[i].key = parseInt(res[i].key)
            }
            return res
        };

        stakes_history_chart
            .width(width)
            .height(null)
            //.margins({top: 10, right: 50, bottom: 20, left: 50})
            //.x(d3.scale.linear().domain([min_x, num_total_bets]))
            .x(d3.scale.linear())
            .centerBar(true)
            //.renderArea(true)
            .elasticY(true)
            .elasticX(true)
            .xAxisPadding("10%")
            .yAxisPadding("10%")
            .renderHorizontalGridLines(true)
            .dimension(total_bets_counter_dim)
            .group(combined_group, "Stake", select_stack(0))
            .stack(combined_group, "Profit", select_stack(1))
            .hidableStacks(true)
            .legend(dc.legend().x(width*(4.1/5)).y(10).gap(5))
            .title('Stake', function(d){
                return 'Stake: ' + d.value[0];
            })
            .title('Profit', function(d){
                return 'Profit: ' + d.value[1];
            })
            .brushOn(true);
            //.colors([colors.default.toString(), tb_win_color.toString()])
        stakes_history_chart.xAxis().ticks(Math.min(num_total_bets, max_x));
        charts[chart_ids[5]] = stakes_history_chart;
        return stakes_history_chart;
    }

    //function deposit_bar_chart(deposit_bar_chart, total_bets_counter_dim, num_total_bets){
    //    ////var decision_date_dim = total_bets_cf.dimension(function(d){return d3.time.week(d.decision_date)});
    //    var by_decision_date_deposit = total_bets_counter_dim.group().reduceSum(function(d){return d.deposit});
    //
    //    ////var minDate = decision_date_dim.bottom(1)[0].decision_date;
    //    ////var maxDate = decision_date_dim.top(1)[0].decision_date;
    //    var num_groups = by_decision_date_deposit.size();
    //
    //    var width = $('#stakes_history_bar_chart').parent().closest('div.portlet-body').width();
    //    var height = null;
    //
    //    deposit_bar_chart
    //        .width(width)
    //        .height(height)
    //        ////.x(d3.time.scale().domain([minDate, maxDate]))
    //        .x(d3.scale.linear().domain([0, num_total_bets+1]))
    //        .centerBar(true)
    //        .elasticY(true)
    //        ////.yAxisLabel("Deposits")
    //        .yAxisPadding("10%")
    //        .renderHorizontalGridLines(true)
    //        .title(function(d){
    //            return "deposit "+ d.value;
    //        })
    //        .brushOn(false)
    //        .controlsUseVisibility(true)
    //        .dimension(total_bets_counter_dim)
    //        .group(by_decision_date_deposit)
    //        .xAxis().ticks(num_groups);
    //    return deposit_bar_chart
    //}

    function total_bets_data_count(data_count_chart, crossfilter){
        var all = crossfilter.groupAll();
        data_count_chart
            .dimension(crossfilter)
            .group(all);
        //<a class="reset" href="javascript:myChart.filterAll(); dc.redrawAll();">Reset</a> //for individual charts
        var reset_all_link = $(".dc-data-count a");
        reset_all_link.attr("href", "javascript:dc.filterAll(); dc.renderAll();");
    }

    function seasons_bubble_chart(seasons_bubble_chart, seasons_dim, num_total_bets) {
        var reduce_functions = stats_reduce_functions(false, num_total_bets);
        var by_season_stats_group = seasons_dim.group().reduce(reduce_functions[0], reduce_functions[1], reduce_functions[2]);

        var width = $('#seasons_bubble_chart').parent().closest('div.portlet-body').width();
        var height = null;
        //Create a bubble chart and use the given css selector as anchor. You can also specify
        //an optional chart group for this chart to be scoped within. When a chart belongs
        //to a specific group then any interaction with the chart will only trigger redraws
        //on charts within the same chart group.
        seasons_bubble_chart
            .width(width)
            .height(height)
            .transitionDuration(1500)
            .margins({top: 10, right: 50, bottom: 30, left: 40})
            .dimension(seasons_dim)
            //The bubble chart expects the groups are reduced to multiple values which are used
            //to generate x, y, and radius for each key (bubble) in the group
            .group(by_season_stats_group)
            // (_optional_) define color function or array for bubbles: [ColorBrewer](http://colorbrewer2.org/)
            .colors(colorbrewer.RdYlGn[9])
            //(optional) define color domain to match your data domain if you want to bind data or color
            .colorDomain([0, 0.00001]) //bellow 0 will be red above 0.00001 will b green

            //##### Accessors
            //Accessor functions are applied to each value returned by the grouping
            // `.colorAccessor` - the returned value will be passed to the `.colors()` scale to determine a fill color
            .colorAccessor(function (d) { return d.value.bank_growth; })
            // `.keyAccessor` - the `X` value will be passed to the `.x()` scale to determine pixel location
            .keyAccessor(function (p) { return p.value.count; })
            // `.valueAccessor` - the `Y` value will be passed to the `.y()` scale to determine pixel location
            .valueAccessor(function (p) { return p.value.amount; })
            // `.radiusValueAccessor` - the value will be passed to the `.r()` scale to determine radius size;
            //   by default this maps linearly to [0,100]
            .radiusValueAccessor(function (p) {return p.value.bank_growth ? Math.abs(p.value.bank_growth) : 1; })

            .maxBubbleRelativeSize(0.3) // maximum size relative to the length of x axis
            .x(d3.scale.linear().domain([0, 500]))
            .y(d3.scale.linear().domain([0, 40]))
            .r(d3.scale.linear().domain([0, 1000]))
            .minRadius(2)

            //##### Elastic Scaling
            .elasticY(true)
            .elasticX(true)
            .yAxisPadding(10)
            .xAxisPadding(50)
            .renderHorizontalGridLines(true)
            .renderVerticalGridLines(true)
            .xAxisLabel('Number of Bets')
            .yAxisLabel('Stakes')

            .controlsUseVisibility(true)

            //##### Labels and  Titles
            //Labels are displayed on the chart for each bubble. Titles displayed on mouseover.
            .renderLabel(true)
            .label(function (p) { return p.key; })
            .renderTitle(true)
            .title(function (p) {
                //glog(p);
                return [
                    'Season ' + p.key,
                    '----',
                    'Bets ROI: ' + p.value.bets_roi.toFixed(1) + '%',
                    'Yield: ' + p.value.yield.toFixed(1) + '%',
                    '----',
                    'Number of bets: ' + p.value.count,
                    //'Bet Investment: ' + p.value.bet_deposits.toFixed(1),
                    'Investment: ' + p.value.real_investment.toFixed(1),
                    'Total Stakes: ' + p.value.amount.toFixed(1),
                    'Pure Wins: ' + p.value.pure_wins.toFixed(1),
                    'Bank Growth: ' + p.value.bank_growth.toFixed(1)
                ].join('\n');
            });

            //#### Customize Axes
            // Set a custom tick format. Both `.yAxis()` and `.xAxis()` return an axis object,
            // so any additional method chaining applies to the axis, not the chart.
            //.yAxis().tickFormat(function (v) { return v ; });
        return seasons_bubble_chart
    }

    function numbers(dim, num_total_bets, real_roi_number, yield_number, bank_growth_number, balance_number,
                     numbets_number, max_stake, median_stake, max_profit, median_profit, max_odd, median_odd,
                     pop_team, pop_competition, pop_bookmaker, pop_market, total_stakes, total_profits, real_investment
    ){
        var reduce_functions = stats_reduce_functions(true, num_total_bets);
        var group = dim.groupAll().reduce(reduce_functions[0], reduce_functions[1], reduce_functions[2]);
        balance_number
            .group(group)
            .valueAccessor(function(p){return p.bank_growth + p.real_investment - p.sum_of_withdrawals;})
            .formatNumber(d3.format('.1f'))
            .html({
                one:'%number',
                some:'%number',
                none:'0'
            })
            .on("renderlet", function(dc_number){
                var number_span = $(balance_number_span);
                if (dc_number.value() >= 0){
                    number_span.removeClass("lost").addClass('won');
                    number_span.closest("div").find("span").removeClass("lost").addClass('won');
                }
                else{
                    number_span.removeClass("won").addClass('lost');
                    number_span.closest("div").find("span").removeClass("won").addClass('lost');
                }
            });
        //roi_number
        //    .group(group)
        //    .valueAccessor(function(p){return p.bets_roi;})
        //    .formatNumber(d3.format('.1f'))
        //    .html({
        //        one:'%number %',
        //        some:'%number %',
        //        none:'0'
        //    })
        //    .on("renderlet", function(dc_number){
        //        var number_span = $(roi_number_span);
        //        if (dc_number.value() >= 0){number_span.removeClass("lost").addClass('won')}
        //        else{number_span.removeClass("won").addClass('lost')}
        //    });
        real_roi_number
            .group(group)
            .valueAccessor(function(p){return p.deposits_roi;})
            .formatNumber(d3.format('.1f'))
            .html({
                one:'%number %',
                some:'%number %',
                none:'0'
            })
            .on("renderlet", function(dc_number){
                var number_span = $(real_roi_number_span);
                if (dc_number.value() >= 0){
                    number_span.removeClass("lost").addClass('won');
                    number_span.closest("div").find("span").removeClass("lost").addClass('won');
                }
                else{
                    number_span.removeClass("won").addClass('lost');
                    number_span.closest("div").find("span").removeClass("won").addClass('lost');
                }
            });
        yield_number
            .group(group)
            .valueAccessor(function(p){return p.yield.toFixed(1);})
            .formatNumber(d3.format('.1f'))
            .html({
                one:'%number %',
                some:'%number %',
                none:'0'
            })
            .on("renderlet", function(dc_number){
                var number_span = $(yield_number_span);
                if (dc_number.value() >= 0){
                    number_span.removeClass("lost").addClass('won');
                    number_span.closest("div").find("span").removeClass("lost").addClass('won');
                }
                else{
                    number_span.removeClass("won").addClass('lost');
                    number_span.closest("div").find("span").removeClass("won").addClass('lost');
                }
            });
        bank_growth_number
            .group(group)
            .valueAccessor(function(p){return p.bank_growth;})
            .formatNumber(d3.format('.1f'))
            .on("renderlet", function(dc_number){
                var number_span = $(bank_growth_number_span);
                if (dc_number.value() >= 0){
                    number_span.removeClass("lost").addClass('won');
                    number_span.closest("div").find("span").removeClass("lost").addClass('won');
                }
                else{
                    number_span.removeClass("won").addClass('lost');
                    number_span.closest("div").find("span").removeClass("won").addClass('lost');
                }
            });
        numbets_number
            .group(group)
            .valueAccessor(function(p){return p.count;})
            .formatNumber(d3.format('d'));
        max_stake
            .group(group)
            .valueAccessor(function(p){return p.max_amount;})
            .formatNumber(d3.format('.1f'));
        median_stake
            .group(group)
            .valueAccessor(function(p){return p.median_amount;})
            .formatNumber(d3.format('.1f'));
        max_profit
            .group(group)
            .valueAccessor(function(p){return p.max_profit;})
            .formatNumber(d3.format('.1f'));
        median_profit
            .group(group)
            .valueAccessor(function(p){return p.median_profit;})
            .formatNumber(d3.format('.1f'));
            //.on("renderlet", function(dc_number){
            //        var number_span = $(average_profit_number_span);
            //        if (dc_number.value() >= 0){number_span.removeClass("lost").addClass('won')}
            //        else{number_span.removeClass("won").addClass('lost')}
            //    });
        max_odd
            .group(group)
            .valueAccessor(function(p){return p.max_odd;})
            .formatNumber(d3.format('.1f'));
        median_odd
            .group(group)
            .valueAccessor(function(p){return p.median_odd;})
            .formatNumber(d3.format('.1f'));
        pop_team
            .group(group)
            .valueAccessor(function(p){return p.pop_team;})
            .formatNumber(function(){return pop_team.value();});
        pop_competition
            .group(group)
            .valueAccessor(function(p){return p.pop_competition;})
            .formatNumber(function(){return pop_competition.value();});
        pop_bookmaker
            .group(group)
            .valueAccessor(function(p){return p.pop_bookmaker;})
            .formatNumber(function(){return pop_bookmaker.value();});
        pop_market
            .group(group)
            .valueAccessor(function(p){return p.pop_market;})
            .formatNumber(function(){return pop_market.value();});
        total_stakes
            .group(group)
            .valueAccessor(function(p){return p.amount;})
            .formatNumber(d3.format('.1f'));
        total_profits
            .group(group)
            .valueAccessor(function(p){return p.pure_wins;})
            .formatNumber(d3.format('.1f'));
        //investment
        //    .group(group)
        //    .valueAccessor(function(p){return p.bet_deposits;})
        //    .formatNumber(d3.format('.1f'));
        real_investment
            .group(group)
            .valueAccessor(function(p){return p.real_investment;})
            .formatNumber(d3.format('.1f'));
    }

    function recent_form_chart(recent_form_chart, counter_dim){
        recent_form_chart
            .dimension(counter_dim)
            // we want all bets to be in the same group, so one tbody will be created (it's tbody per group)
            // with one row for each tb. Then the rows are sorted based on the sort_by property
            .group(function(d){ return 'common group'; })
            // the data will be fetched by dimension.top(size) or bottom(size) depending on the value of .order
            // The number of records is defined by the .size property. The data are then sorted by the .sortBy
            .order(d3.descending)
            .size(15)
            .sortBy(function (d) {return d.counter;})
            .columns([
                {
                    label: '',
                    format: function(d){
                        var res; if (d.status === tb_status_won){res = 'W'}else if(d.status == tb_status_lost){res = 'L'}else{res = 'O'}
                        return res
                    }
                }
            ])
            .showGroups(false)
            .on('renderlet', function (table) {
                table.selectAll('.dc-table-column').each(function(d){
                    var col = d3.select(this);
                    // d are the data object
                    if (d.status === tb_status_won){
                        //col.classed('won', true);
                        col.attr('style', "background-color:" + tb_win_color);
                    }else if(d.status == tb_status_lost){
                        //col.classed('lost', true);
                        col.attr('style', "background-color:" + tb_loss_color);
                    }else{
                        //col.classed('info', true);
                        col.attr('style', "background-color:" + tb_open_color);
                    }
                });
            });
    }

    function countries_select(chart, array_dim){
        chart
            .dimension(array_dim)
            .group(array_dim.group())
            .controlsUseVisibility(true)
            //.multiple(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true).attr('id', 'countries_select_elem');
                //var $select2_elem = $('#countries_select_elem').select2({
                //    placeholder: 'Select Countries',
                //    allowClear: true
                //});
            });
        charts[chart_ids[6]] = chart;
    }

    function competitions_select(chart, array_dim){
        chart
            .dimension(array_dim)
            .group(array_dim.group())
            .controlsUseVisibility(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true);
            });
        charts[chart_ids[7]] = chart;
    }

    function seasons_select(chart, dim){
        chart
            .dimension(dim)
            .group(dim.group())
            .controlsUseVisibility(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true);
            });
        charts[chart_ids[8]] = chart;
    }

    function home_teams_select(chart, array_dim){
        chart
            .dimension(array_dim)
            .group(array_dim.group())
            .controlsUseVisibility(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true);
            });
        charts[chart_ids[9]] = chart;
    }

    function away_teams_select(chart, array_dim){
        chart
            .dimension(array_dim)
            .group(array_dim.group())
            .controlsUseVisibility(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true);
            });
        charts[chart_ids[10]] = chart;
    }

    function tb_bevs_num(chart, dim){
        chart
            .dimension(dim)
            .group(dim.group())
            .controlsUseVisibility(true)
            .on("renderlet", function(chart){
                var select_menu = chart.select('select.dc-select-menu').classed('form-control select2', true);
            });
        charts[chart_ids[11]] = chart;
    }

    return {
        bind_events: bind_events,
        total_bets_status_pie: total_bets_status_pie,
        bank_growth_history_chart: bank_growth_history_chart,
        bank_growth_history_bar_chart: bank_growth_history_bar_chart,
        stakes_history_bar_chart: stakes_history_bar_chart,
        //deposit_bar_chart: deposit_bar_chart,
        total_bets_data_count: total_bets_data_count,
        time_bar_chart: time_bar_chart,
        seasons_bubble_chart: seasons_bubble_chart,
        numbers: numbers,
        recent_form_chart: recent_form_chart,
        //bet_tag_filtering: bet_tag_filtering
        countries_select: countries_select,
        competitions_select: competitions_select,
        seasons_select: seasons_select,
        home_teams_select: home_teams_select,
        away_teams_select: away_teams_select,
        tb_bevs_num: tb_bevs_num
    }
});

