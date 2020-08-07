/**
 * Created by xene on 4/5/2016.
 */

define([
    'jquery',
    'd3',
    'crossfilter',
    'dc',
    'js/utils',
    'js/urls',
    './total_bets_charts',
    './bet_events_charts'
    //'./filters'
], function($, d3, crossfilter, dc, Utils, Urls, Total_bets_charts, Bet_events_charts){

    var config = {
        debug: Utils.config.logger.bet_statistics,
        urls: Urls,
        profile_charts_wrapper_id: "#profile_charts_wrapper",
        loading_wrapper_class: "loading_wrapper",
        main_container: "#main_container"
    };

    var log = Utils.create_logger(config.debug);
    var urls = config.urls;
    var profile_charts_wrapper_id = config.profile_charts_wrapper_id;
    var loading_wrapper_class = config.loading_wrapper_class;
    var main_container = config.main_container;
    var charts = [];
    var total_bets_cf = null;
    var bet_events_cf = null;
    var dimensions = {};

    function get_profile_data(user_pk){
        log('getting profile json data...');
        var profile_data_url = urls.stats.profile_data + user_pk + "/";
        $.ajax({
            type: 'GET',
            url: profile_data_url,
            datatype: 'json',
            success: function(jsondata){
                log('profile json data received');
                //console.log(jsondata);
                // jquery automatically converts the received json data to a js object. In my case the js object contains
                // some json strings that also need to be parsed. I do this parsing manually
                render_template(jsondata);
            },
            error: function(){
                no_profile_data();
                //log(null, 'profile data not received')
            }
        });
    }

    function parse_dates(total_bets, tbs_by_date, bet_events, date_format){
        // todo convert to local timezone or send local dates from server
        var parseDate = d3.time.format(date_format).parse;
        total_bets.forEach(function(d) {
            //console.log("d.date before d3 parsing: ", d.date, typeof (d.date));
            d.date = parseDate(d.date);
            //console.log("d.date after d3 parsing: ", d.date, typeof (d.date));
            try{
                d.decision_date = parseDate(d.decision_date);}
            catch(error) {
                // open bets have null decision date which raises a d3.js error when parsing the date.
                // In this case we set manually the decision date to be null (as it was).
                // As of now the decision_date is not used in the charts
                d.decision_date = null;
            }
        });
        tbs_by_date.forEach(function(d){
            // the by_date_df can have either a decision_date or a date column
            if (d.decision_date){d.decision_date = parseDate(d.decision_date)}
            else if(d.date){d.date = parseDate(d.date)}
        });
        bet_events.forEach(function(d){
            d.event_date = parseDate(d.event_date)
        });
        //return [total_bets, tbs_by_date, bet_events]
    }

    function add_counter_column(json_array){
        // we add a counter "column" to the total bets. The counter is analogous to the decision date since the total bets
        // are sorted by the decision date (in pandas). Small counter means old total bet, big means new.
        var counter = 1;
        json_array.forEach(function(d){
            d.counter = counter;
            counter += 1;
        });
    }

    //function add_deposit_column(json_array){
    //    //// deposit column is no longer used.
    //    var i = 0;
    //    var investment_array = [];
    //    json_array.forEach(function(d){
    //        if (i == 0){d.deposit = d.amount}
    //        else{
    //            var current_max = Math.max.apply(null, investment_array);
    //            d.investment > current_max ? d.deposit = d.investment-current_max : d.deposit = 0
    //        }
    //        investment_array.push(d.investment);
    //        i += 1;
    //    });
    //}

    function getUniqueArray(value, index, self) {
        return self.indexOf(value) === index;
    }

    function join_json_arrays(total_bets, bet_events){
        //maybe this process could be done faster by django rest framework (nested objects) or manually with pandas
        var tbs_without_bevs_idx = [];
        var counter = 0;
        total_bets.forEach(function(tb){
            tb.markets = [];
            tb.bet_event_statuses = [];
            tb.bet_event_choices = [];
            tb.home_teams = [];
            tb.away_teams = [];
            tb.competitions = [];
            tb.countries = [];
            tb.bet_event_ids = [];
            tb.season = undefined;
            var tb_id = tb.total_bet_id;
            bet_events.forEach(function(bev){
                if (bev.total_bet_id === tb_id){
                    tb.markets.push(bev.market_type);
                    tb.bet_event_statuses.push(bev.selection_status);
                    tb.bet_event_choices.push(bev.choice);
                    tb.home_teams.push(bev.home_team);
                    tb.away_teams.push(bev.away_team);
                    tb.competitions.push(bev.competition_generic_name);
                    tb.countries.push(bev.country);
                    tb.bet_event_ids.push(bev.bet_event_id);
                    tb.season = bev.season
                }
            });
            if (tb.bet_event_ids.length == 0){
                // the index of a tb that has no bet_events
                tbs_without_bevs_idx.push(counter);
            }
            counter += 1
        });
        return tbs_without_bevs_idx
    }

    function remove_tbs(total_bets, tbs_without_bevs_idx){
        if (tbs_without_bevs_idx){
            log("removing total_bets without bet_events...");
            for (var i=tbs_without_bevs_idx.length-1; i>=0; i--){
                // removing from the end not to destroy the indexing for removal
                log('total bet to remove: ', total_bets[tbs_without_bevs_idx[i]]);
                total_bets.splice(tbs_without_bevs_idx[i], 1)
            }
        }
    }

    function modify_date_of_open_tbs(total_bets, tbs_by_date, bet_events){
        //var maxDate=new Date(Math.max.apply(null,dates_array));
    }

    function pre_process_json_data(total_bets, tbs_by_date, bet_events){
        var tbs_without_bevs_idx = join_json_arrays(total_bets, bet_events);
        remove_tbs(total_bets, tbs_without_bevs_idx);
        //the format of the dates which need to be read (the date format of the profile data json response)
        var date_format = "%Y-%m-%dT%H:%M:%S.%LZ";
        parse_dates(total_bets, tbs_by_date, bet_events, date_format);
        add_counter_column(total_bets);
        //add_deposit_column(total_bets);
    }

    function create_total_bet_charts(total_bets_cf, groups){
        var status_pie = dc.pieChart("#status_pie");
        var time_bar_chart = dc.barChart("#time_bar_chart");
        var bank_growth_history_chart = dc.lineChart("#bank_growth_history_chart", groups[0]);
        dc.registerChart(bank_growth_history_chart, groups[0]);
        var stakes_history_chart = dc.barChart("#stakes_history_bar_chart");
        var bank_growth_history_bar_chart = dc.barChart("#bank_growth_history_bar_chart");
        //var deposit_bar_chart = dc.barChart("#deposit_bar_chart");
        var data_count_chart = dc.dataCount("#dc-data-count");
        var seasons_bubble_chart = dc.bubbleChart("#seasons_bubble_chart");
        var recent_form_chart = dc.dataTable("#recent_form_chart");

        //var roi_number = dc.numberDisplay("#roi_number");
        var real_roi_number = dc.numberDisplay("#real_roi_number");
        var yield_number = dc.numberDisplay("#yield_number");
        var bank_growth_number = dc.numberDisplay("#bank_growth_number");
        var balance_number = dc.numberDisplay("#balance_number");

        var numbets_number = dc.numberDisplay("#numbets_number");
        var max_stake = dc.numberDisplay("#max_stake");
        var median_stake = dc.numberDisplay("#median_stake");
        var max_profit = dc.numberDisplay("#max_profit");
        var median_profit = dc.numberDisplay("#median_profit");
        var max_odd = dc.numberDisplay("#max_odd");
        var median_odd = dc.numberDisplay("#median_odd");
        var pop_team = dc.numberDisplay("#pop_team");
        var pop_competition = dc.numberDisplay("#pop_competition");
        var pop_bookmaker = dc.numberDisplay("#pop_bookmaker");
        var pop_market = dc.numberDisplay("#pop_market");
        var total_stakes = dc.numberDisplay("#total_stakes_number");
        var total_profits = dc.numberDisplay("#total_profits_number");
        //var investment = dc.numberDisplay("#investment_number");
        var real_investment = dc.numberDisplay("#real_investment_number");

        // selectMenu is introduced in dc v2.1.0
        var countries_select = dc.selectMenu("#countries_dc_select");
        var competitions_select = dc.selectMenu("#competitions_dc_select");
        var seasons_select = dc.selectMenu("#seasons_dc_select");
        var home_teams_select = dc.selectMenu("#home_teams_dc_select");
        var away_teams_select = dc.selectMenu("#away_teams_dc_select");
        var tb_bevs_num_select = dc.selectMenu("#bevs_num_dc_select");

        var tb_countries = total_bets_cf.dimension(function(d){return d.countries}, true);
        var tb_competitions = total_bets_cf.dimension(function(d){return d.competitions}, true);
        var tb_home_teams = total_bets_cf.dimension(function(d){return d.home_teams}, true);
        var tb_away_teams = total_bets_cf.dimension(function(d){return d.away_teams}, true);
        var tb_bevs_num = total_bets_cf.dimension(function(d){return d.competitions.length});

        var totalBetStatusDim = total_bets_cf.dimension(function (d) {return d.status;});
        //var decision_date_dim = total_bets_cf.dimension(function(d){ return d3.time.day(d.decision_date); });
        var date_dim = total_bets_cf.dimension(function(d){ return d3.time.day(d.date); });
        // If I used the same dimension the relative charts weren't interactive in between them
        // if I used the brush of one of them the others weren't updated
        // Two charts on the same dimension will not filter each other. More precisely, a group will not
        // observe filters on its own dimension. This is the design of crossfilter
        var counter_dim_1 = total_bets_cf.dimension(function(d){ return d.counter;});
        var counter_dim_2 = total_bets_cf.dimension(function(d){ return d.counter;});
        //var counter_dim_3 = total_bets_cf.dimension(function(d){ return d.counter;});
        //var counter_dim_4 = total_bets_cf.dimension(function(d){ return d.counter;});
        var seasons_dim = total_bets_cf.dimension(function (d) {return d.season;});
        var seasons_dim_02= total_bets_cf.dimension(function (d) {return d.season;});

        // // if bet_tags_dim was an array dimension (supported only in crossfilter 1.4.x)
        // // dimensions.bet_tags_dim = total_bets_cf.dimension(function(d){return d.bet_tag_name}, true);
        // bet_tags_dim is used for manual filtering
        dimensions.bet_tags_dim = total_bets_cf.dimension(function(d){return d.bet_tag_name});
        dimensions.tb_ids_dim = total_bets_cf.dimension(function(d){return d.total_bet_id});

        var num_total_bets = total_bets_cf.size();
        //var tbs_table = dc.dataTable("#bev_dc_table");
        //var tbs_dc_chart = Bet_events_charts.tbs_table(date_dim, tbs_table);

        Total_bets_charts.countries_select(countries_select, tb_countries);
        Total_bets_charts.competitions_select(competitions_select, tb_competitions);
        Total_bets_charts.seasons_select(seasons_select, seasons_dim_02);
        Total_bets_charts.home_teams_select(home_teams_select, tb_home_teams);
        Total_bets_charts.away_teams_select(away_teams_select, tb_away_teams);
        Total_bets_charts.tb_bevs_num(tb_bevs_num_select, tb_bevs_num);

        Total_bets_charts.recent_form_chart(recent_form_chart, counter_dim_1);
        var status_pie_dc_chart = Total_bets_charts.total_bets_status_pie(status_pie, totalBetStatusDim);
        Total_bets_charts.total_bets_data_count(data_count_chart, total_bets_cf);
        var time_bar_dc_chart = Total_bets_charts.time_bar_chart(time_bar_chart, date_dim);
        Total_bets_charts.bank_growth_history_chart(bank_growth_history_chart, date_dim, time_bar_chart);
        var bank_growth_history_dc_bar_chart = Total_bets_charts.bank_growth_history_bar_chart(bank_growth_history_bar_chart, counter_dim_1, num_total_bets);
        Total_bets_charts.stakes_history_bar_chart(stakes_history_chart, counter_dim_1, num_total_bets);
        //var deposit_bar_dc_chart = Total_bets_charts.deposit_bar_chart(deposit_bar_chart, counter_dim_1, num_total_bets);
        var seasons_bubble_dc_chart = Total_bets_charts.seasons_bubble_chart(seasons_bubble_chart, seasons_dim, num_total_bets);
        Total_bets_charts.numbers(
            counter_dim_2, num_total_bets, /*roi_number,*/ real_roi_number, yield_number, bank_growth_number, balance_number,
            numbets_number, max_stake, median_stake, max_profit, median_profit, max_odd, median_odd,
            pop_team, pop_competition, pop_bookmaker, pop_market, total_stakes, total_profits, /*investment,*/ real_investment
        );

        charts.push(status_pie_dc_chart, time_bar_dc_chart, bank_growth_history_dc_bar_chart, /* deposit_bar_dc_chart, */ seasons_bubble_dc_chart);
    }

    function create_bet_event_charts(bet_events_cf, total_bets_cf, total_bets){
        var market_pie = dc.pieChart("#bet_events_market_pie");
        var choice_pie = dc.pieChart("#bet_events_choice_pie");
        var status_pie = dc.pieChart("#bet_events_status_pie");
        var bev_dc_table = dc.dataTable("#bev_dc_table");

        //var date_dim = bet_events_cf.dimension(function(d){return [d.total_bet_id, d.event_date];});
        var date_dim = bet_events_cf.dimension(function(d){return d.event_date;});
        var betEventsChoiceDim = bet_events_cf.dimension(function (d) {return d.choice;});
        var betEventsStatusDim = bet_events_cf.dimension(function (d) {return d.selection_status;});

        //var bet_event_ids_dim = bet_events_cf.dimension(function(d){return d.bet_event_id;});
        // The tb_ids_bev_dim is used only for manual filtering, not directly by a chart. (It is used instead of the
        // bet_event_ids_dim)
        var tb_ids_bev_dim = bet_events_cf.dimension(function(d){return d.total_bet_id;});

        var bev_choice_dc_chart = Bet_events_charts.bet_events_choice_pie(choice_pie, betEventsChoiceDim);
        var bev_status_dc_chart = Bet_events_charts.bet_events_status_pie(status_pie, betEventsStatusDim);
        var bev_table_dc_chart = Bet_events_charts.bev_table(date_dim, bev_dc_table, total_bets, dimensions.tb_ids_dim);
        // IMPORTANT: The bev_market_dc_chart must be the LAST one to be rendered (see notes in it)
        var bev_market_dc_chart = Bet_events_charts.bet_events_market_pie(market_pie, total_bets_cf, dimensions.tb_ids_dim, tb_ids_bev_dim);

        charts.push(bev_choice_dc_chart, bev_status_dc_chart, bev_table_dc_chart, bev_market_dc_chart);
    }

    function show_template(elem_to_show_id, elem_to_hide_class){
        log("showing template");
        var elem_to_show = $(elem_to_show_id);
        var elem_to_hide = $("div."+elem_to_hide_class);
        elem_to_hide.addClass("hidden");
        elem_to_show.removeClass("hidden");
    }

    function no_profile_data(){
        // TODO HIGH create a generic messages div
        log("no profile data");
        var temp_elem_id = 'temp_message';
        var elem_to_hide = $("div."+loading_wrapper_class);
        elem_to_hide.addClass("hidden");
        $(main_container).append('div').attr('id', temp_elem_id).html("There is nothing here...").addClass("text-center");
        setTimeout(function() {
            // Removing the added div, because if the next page was a pjax one that replaces the main container
            // the main container is moved bellow the new added div and so the layouts doesn't looks the same
            $('#'+temp_elem_id).remove();
        }, 2000);
    }

    //function fix_height(){
    //    var maxHeight = 0;
    //
    //    $(".r2_box").each(function () {
    //        if ($(this).height() > maxHeight) {
    //            maxHeight = $(this).height();
    //        }
    //    });
    //
    //    $(".r2_box").height(maxHeight);
    //}

    function render_template(jsondata){
        log('rendering template...');
        //console.debug('json tbs', jsondata.tbs);

        var total_bets = JSON.parse( jsondata.tbs );
        log('total_bets', total_bets);
        var tbs_by_date = JSON.parse(jsondata.tbs_by_date);
        log('by date', tbs_by_date);
        var bet_events = JSON.parse(jsondata.bevs);
        log('bet_events', bet_events);

        if (total_bets && bet_events){
            show_template(profile_charts_wrapper_id, loading_wrapper_class);

            pre_process_json_data(total_bets, tbs_by_date, bet_events);

            var groups = ["group_0"];
            total_bets_cf = crossfilter(total_bets);
            create_total_bet_charts(total_bets_cf, groups);

            bet_events_cf = crossfilter(bet_events);
            create_bet_event_charts(bet_events_cf, total_bets_cf, total_bets);
            log("before rendering");
            dc.renderAll();
            dc.renderAll(groups[0]);

        } else{
            //no_profile_data();
            //$("#profile_messages").html("No data available...")
            total_bets = [];
            bet_events = [];
            show_template(profile_charts_wrapper_id, loading_wrapper_class);

            var groups = ["group_0"];
            total_bets_cf = crossfilter(total_bets);
            create_total_bet_charts(total_bets_cf, groups);
            bet_events_cf = crossfilter(bet_events);
            create_bet_event_charts(bet_events_cf, total_bets_cf, total_bets);
            log("before rendering");
            dc.renderAll();
            dc.renderAll(groups[0]);
        }

        $(document).trigger('profile_charts_rendered');
        $(document).trigger('rendered_with_json');
        log('rendering done')
    }

    function initialize(){
        $('#profile_description_chart').slimScroll({
            height: '250px',
            color: '#21282e',
            // alwaysVisible: true,
            railVisible: true,
            // railColor: '#21282e',
            allowPageScroll: false,
            disableFadeOut: true
        });
    }

    return {
        get_profile_data: get_profile_data,
        charts: charts,
        dimensions: dimensions,
        total_bets_cf: total_bets_cf,
        bet_events_cf: bet_events_cf,
        init: initialize
    }
});

