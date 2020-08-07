/**
 * Created by xene on 7/13/2016.
 */

define([
    'jquery',
    'js/utils',
    'js/urls',
    'datatables.net'
], function($, Utils, Urls) {
    var config = {
        debug: Utils.config.logger.bet_statistics,
        table_wrapper: '#leaderboard_table_wrapper',
        leaderboard_table_id: "#leaderboard",
        leaderboard_links_class: "leaderboard",
        loading_wrapper_class: "loading_wrapper"
    };

    var log = Utils.create_logger(config.debug);
    //var $leaderboard = $(config.leaderboard_table_id); // didn't work why?
    var leaderboard_table_id = config.leaderboard_table_id;
    var leaderboard_links_class = config.leaderboard_links_class;
    var leaderboard_data_url = Urls.stats.leader_board_data;
    var profile_template_url = Urls.stats.profile_template;
    var stored_leaderboard_data = null;
    var datatable_obj = null;

    function populate_table(table_id, data){
        var $table = $(table_id);

        for (var i=0; i<data.length; i++){
            // creating an index column
            data[i].index = 0;
        }

        var $loading_wrapper = $("div."+config.loading_wrapper_class);
        datatable_obj = $table.DataTable({
            "data": data,
            "columns": [
                {"data": "index", "searchable": false, "orderable": false},
                {
                    "data": "user_info",
                    "className": 'bg_zak_dark align_center',
                    "render": function (d, type, row, meta) {
                        return '<a class="pjax_call dark_back s13" href="' + profile_template_url + d.user_id + '">' + d.username + '</a>';
                        //return '<a class="pjax_call_left_main" href="' + profile_template_url + d.user_id + '">' + d.username + '</a>';
                    }
                },
                { "data": "yield", "render": function (d, type, row, meta) {return d.toFixed(3)} },
                { "data": "roi", "render": function (d, type, row, meta) {return d.toFixed(3)} },
                { "data": "bank_growth", "render": function (d, type, row, meta) {return d.toFixed(3)} },
                { "data": "investment", "render": function (d, type, row, meta) {return d.toFixed(3)} },
                { "data": "wins_losses" }
            ],
            "order": [[ 2 ]],
            "orderClasses": false
        });

        datatable_obj.on('order.dt', function() {
            // In order events on the leader board table, the index column is recalculated. Not in search in order
            // to be able to see the position of a user if you search for him
            datatable_obj.column(0, {order: 'applied'}).nodes().each(function (cell, i) {
                cell.innerHTML = i + 1;
            })
        }).draw();

        $loading_wrapper.addClass("hidden");
        $(config.table_wrapper).removeClass("hidden");
        datatable_obj.columns.adjust();
        datatable_obj.responsive.recalc();

        $(document).trigger('rendered_with_json');
    }

    function get_leaderboard_data(){
        if(!stored_leaderboard_data){
            // TODO consider storing also the profile json data in profile_stats.js (for each user)
            $.ajax({
                type: 'GET',
                url: leaderboard_data_url,
                datatype: 'json',
                success: function (json_data) {
                    glog("leaderboard data received: ", json_data);
                    populate_table(leaderboard_table_id, json_data);
                    stored_leaderboard_data = json_data;
                },
                error: function () {
                    populate_table(leaderboard_table_id, []);
                    var $table = $(leaderboard_table_id);
                    var $loading_wrapper = $("div."+config.loading_wrapper_class);
                    $loading_wrapper.addClass("hidden");
                    $table.removeClass("hidden");
                    log(null, 'leaderboard data not received');
                    $.bootstrapGrowl('Ooops! Data not received. Please reload the page!', {type: 'danger', align: 'center'});
                }
            })
        }else{
            glog("using stored leaderboard data", stored_leaderboard_data);
            populate_table(leaderboard_table_id, stored_leaderboard_data)
        }
    }

    function bind_events(){
        $(document).on("click", "a."+leaderboard_links_class, function(){
            get_leaderboard_data();
        });
    }

    return{
        bind_events: bind_events,
        get_leaderboard_data: get_leaderboard_data
    }
});
