/**
 * Created by xene on 8/4/2016.
 */

define([
    'jquery',
    'js/utils',
    'js/urls',
    'moment',
    'datatables.net',
    'datatables_responsive'
], function($, Utils, Urls, Moment) {
    var config = {
        debug: Utils.config.logger.bet_statistics,
        // debug: true,
        closed_bevs_table_id: "#closed_bet_events_table",
        open_bevs_table_id: "#open_bet_events_table",
        loading_wrapper_class: "loading_wrapper",
        bet_events_tabs_wrapper: "#bet_events_tabs_wrapper"
    };

    var log = Utils.create_logger(config.debug);
    var bevs_table_data_url = Urls.stats.bet_events_table_data;
    var event_url_body = Urls.games.event;
    var tb_url_body = Urls.stats.total_bet_detail;
    var bet_events_tabs_wrapper = config.bet_events_tabs_wrapper;
    var closed_table_id = config.closed_bevs_table_id;
    var open_table_id = config.open_bevs_table_id;
    var emptyBevTable_text = {};
    emptyBevTable_text[open_table_id] = 'You have no Open Bet Events!';
    emptyBevTable_text[closed_table_id] = 'You have no Closed Bet Events!';
    var date_format = "ddd DD MMM YYYY HH:mm";
    var order_date_format = "YMDHHmm";

    var open_str = Utils.config.status.Open;
    var won_str = Utils.config.status.Won;
    var lost_str = Utils.config.status.Lost;
    var void_str = Utils.config.status.Void;
    var won_class = Utils.config.status_class.won;
    var lost_class = Utils.config.status_class.lost;
    var void_class = Utils.config.status_class.void;

    var in_tab_datatables = Utils.datatables;
    var other_datatables = [];
    var stored_data = {};

    function populate_table(table_id, data, normalization_method){
        log(" ----- normalization_method: ", normalization_method);
        var $table = $(table_id);

        for (var i=0; i<data.length; i++){
            // creating an index column
            data[i].index = 0;
        }
        //alert(Moment().format('dddd, MMMM Do YYYY, h:mm:ss a'));
        var datatable_obj = $table.DataTable({
            "data": data,

            // Internationalisation. For more info refer to http://datatables.net/manual/i18n
            "language": {
                //"aria": {
                //    "sortAscending": ": activate to sort column ascending",
                //    "sortDescending": ": activate to sort column descending"
                //},
                //// As the property names do not contain any special characters you can remove the quotes
                //// for example emptyTable instead of "emptyTable"
                "emptyTable": emptyBevTable_text[table_id]
                //"info": "Showing _START_ to _END_ of _TOTAL_ entries",
                //"infoEmpty": "No entries found",
                //"infoFiltered": "(filtered1 from _MAX_ total entries)",
                //"lengthMenu": "_MENU_ entries",
                //"search": "Search:",
                //"zeroRecords": "No matching records found"
            },

            "columns": [
                {"data": null, "defaultContent": "", orderable: false, className: 'control' },
                {"data": "index", "searchable": false, "orderable": false},
                {
                    "data": "event_date",
                    className: 'no_wrap',
                    "render": function(d, type, row, meta){
                        var localDate = Moment(d).format(date_format);
                        return localDate
                    }
                },
                {
                    "data": "event_id",
                    className: 'bg_zak_dark mobile tablet desktop',
                    "render": function (d, type, row, meta) {
                        // row contains all the data of the row
                        var event_text = row.home_team + ' - ' + row.away_team;
                        var event_url = null;
                        if (row.selection_status === 'Open'){
                            event_url = event_url_body + d + '/';
                        }else{
                            var tb_url = tb_url_body + row.total_bet_id + '/';
                            event_url = tb_url;
                        }
                        return '<a class="pjax_call" href="' + event_url + '">' + '<span class="label label-sm label-info label_zak_d1">' + event_text + '</span>' + '</a>';
                    }
                },
                {
                    "data": "choice" ,
                    className: 'bg_zak_orange',
                    "render": function (d, type, row, meta) {
                        return '<span class="label label-sm label-info label_zak_l1">' + row.choice + '</span>';
                    }
                },
                { "data": "market_type", className: 'no_wrap'},
                {
                    "data": "selection_status",
                    className: 'bev_status',
                    "render": function(d, type, row, meta){
                        return '<span class="label label-sm">' + d + '</span>'
                    }
                },
                {
                    "data": "home_goals",
                    "render": function(d, type, row, meta){
                        var result_text = row.home_goals + '-' + row.away_goals;
                        if (row.home_goals || row.away_goals == 'None'){result_text = '-'}
                        return result_text
                    }
                },
                {
                    "data": "total_bet_id",
                    "render": function (d, type, row, meta) {
                        var tb_url = tb_url_body + d + '/';
                        return '<a class="pjax_call url_param_dependent" href="' + tb_url + '">' + d + '</a>';
                    }
                },
                {
                    "data": "total_bet_amount",
                    "render": function(d, type, row, meta){
                        if (normalization_method == Utils.config.normalization_methods.percent){
                            return d.toFixed(1) + ' %'
                        }else if(normalization_method == Utils.config.normalization_methods.unit){
                            return d.toFixed(3) + ' units'
                        }else{
                            return d.toFixed(3)
                        }
                    }
                },
                { "data": "round" },
                { "data": "competition_generic_name", className: 'no_wrap' },
                { "data": "country" },
                { "data": "season" }
            ],
            responsive: {
                details: {
                    display: $.fn.dataTable.Responsive.display.childRow,
                    type: 'column'
                }
            },
            "order": [[ 2, 'desc' ], [ 8, 'desc' ]],
            "orderClasses": false,
            "createdRow": function( row, rdata, dataIndex ) {
                $( row )
                    // Set the data-order attribute of the event_date cell
                    .find('td:eq(2)')
                    .attr('data-order', Moment(rdata.event_date).format(order_date_format));
                if (rdata.selection_status === lost_str){
                    $(row).find('td.bev_status').find('span').addClass('lost');
                }else if(rdata.selection_status === won_str){
                    $(row).find('td.bev_status').find('span').addClass('won');
                }else if(rdata.selection_status === void_str){
                    $(row).find('td.bev_status').find('span').addClass('label-default');
                }else{
                    $(row).find('td.bev_status').find('span').addClass('label-info');
                }
            }
        });

        in_tab_datatables[table_id] = datatable_obj;

        datatable_obj.on('order.dt search.dt', function() {
            // In order and search events on the leader board table, the index column is recalculated
            //console.log("this:", $(this));
            datatable_obj.column(1, {search: 'applied', order: 'applied'}).nodes().each(function (cell, i) {
                cell.innerHTML = i + 1;
            })
        }).draw();

        datatable_obj.on('draw.dt', function(e){
            log('tb draw event', datatable_obj);
        });

        show_template([datatable_obj]);
        $(document).trigger('rendered_with_json');
        return datatable_obj
    }

    function show_template(datatable_objects){
        var $loading_wrapper = $("div."+config.loading_wrapper_class);
        $loading_wrapper.addClass("hidden");
        $(bet_events_tabs_wrapper).removeClass("hidden");
        if (datatable_objects){
            for (var i = 0; i < datatable_objects.length; i++) {
                datatable_objects[i].columns.adjust();
                // IMPORTANT: if the table is hidden on page show then no width is calculated for the responsive table
                // so you must manually calculate it when the table becomes visible
                datatable_objects[i].responsive.recalc();
            }
        }
    }

    function split_closed_and_open(data, open_str){
        var closed = data.slice(); // copy data
        var open = closed.slice();

        for (var i=data.length-1; i>=0; i--){
            if (data[i].selection_status === open_str){
                closed.splice(i, 1);
            }else{
                open.splice(i, 1)
            }
        }
        return {'open': open, 'closed': closed}
    }

    // TODO create a generic get_data function (common for profile, leader board, bevs table data)
    function get_data(target_user_id){
        var $open_table = $(open_table_id);
        var $closed_table = $(closed_table_id);

        if($.isEmptyObject(stored_data)){
            // this is the ECMA5 way but jquery is cross browser compatible
            // Object.keys(obj).length === 0 && obj.constructor === Object
            var url = bevs_table_data_url + target_user_id;
            $.ajax({
                type: 'GET',
                url: url,
                datatype: 'json',  // jquery automatically parse the data to a js object
                success: function (data) {
                    log("bet events json data received: ", data);
                    var bevs_array = JSON.parse(data.bevs);  // bevs needs parsing since it was jsoned 2 times in server
                    var normalization_method = data.normalization_method;
                    var res = split_closed_and_open(bevs_array, open_str);
                    var open_datatable = populate_table(open_table_id, res.open, normalization_method);
                    var closed_datatable = populate_table(closed_table_id, res.closed, normalization_method);
                    // I must store data for each user the bet_events of whom the request_user sees. So if he sees
                    // his bevs nad another users bevs the correct stored data is used. So I must get the id from
                    // the url ot the link's href and use it to get the correct stored data. (id must be in the url)
                    //stored_data['open'] = res.open;
                    //stored_data['closed'] = res.closed;
                },
                error: function () {
                    var open_datatable = populate_table(open_table_id, [], null);
                    var closed_datatable = populate_table(closed_table_id, [], null);
                    show_template();
                    log(null, 'data not received');
                    $.bootstrapGrowl('An error occurred. Please reload the page!', {type: 'danger', align: 'center'});
                }
            })
        }else{
            log("using stored data", stored_data);
            var open_datatable = populate_table(open_table_id, stored_data['open'], null);
            var closed_datatable = populate_table(closed_table_id, stored_data['closed'], null);
        }
    }

    // TOTAL BETS RELATED CODE //

    function init() {
        var table_ids = ['#open_user_total_bets', '#closed_user_total_bets', '#user_tips_datatable'];
        var emptyTable_text = {
            '#open_user_total_bets': 'It seems that there are no Open Bets to show!',
            '#closed_user_total_bets': 'It seems that there are no Closed Bets to show!',
            '#user_tips_datatable': "It seems that your tipsters haven't picked bets yet!"
        };
        var order_obj = {
            '#open_user_total_bets': [[3, "desc"]],
            '#closed_user_total_bets': [[3, "desc"]],
            '#user_tips_datatable': [[3, "desc"]]
        };
        for (var i = 0; i < table_ids.length; i++) {
            if (!$.fn.DataTable.isDataTable(table_ids[i])) {
                var datatable = $(table_ids[i]).DataTable({
                    "language": {
                        "emptyTable": emptyTable_text[table_ids[i]]
                    },
                    responsive: {
                        details: {
                            display: $.fn.dataTable.Responsive.display.childRow,
                            type: 'column'
                        }
                    },
                    columnDefs: [{
                        className: 'control',
                        orderable: false,
                        targets: 0
                    }],
                    "order": order_obj[table_ids[i]],
                    "orderClasses": false
                });
                in_tab_datatables[table_ids[i]] = datatable;  // there are events attached to the tables of the datatables var
                //datatable.on('order.dt search.dt', function() {
                //    console.log('this', this);
                //    datatable.columns.adjust();
                //    datatable.responsive.recalc();
                //}).draw();
            }
        }

        var table_ids = ['#tb_detail_table', '#bev_detail_table'];
        var emptyTable_text = {
            '#tb_detail_table': 'No Bet selected...',
            '#bev_detail_table': 'No Bet Event selected...'
        };
        var order_obj = {
            '#tb_detail_table': [[6, "desc"]],
            '#bev_detail_table': [[6, "desc"]]
        };
        for (var i = 0; i < table_ids.length; i++) {
            if (!$.fn.DataTable.isDataTable(table_ids[i])) {
                var datatable = $(table_ids[i]).DataTable({
                    "language": {
                        "emptyTable": emptyTable_text[table_ids[i]]
                    },
                    responsive: {
                        details: {
                            display: $.fn.dataTable.Responsive.display.childRow,
                            type: 'column'
                        }
                    },
                    columnDefs: [{
                        className: 'control',
                        orderable: false,
                        targets: 0
                    }],
                    "pageLength": 50,
                    "order": order_obj[table_ids[i]],
                    "orderClasses": false
                });
                other_datatables.push(datatable);
                // datatable.on( 'responsive-resize', function ( e, datatable, columns ) {
                // couldn't make this work, do it
                //     console.log("responsive-resize");
                //    datatable.columns.adjust();
                //    datatable.responsive.recalc();
                // }).draw();
            }
        }

        var users_table_class = "users_table";
        var counter = 0;
        var users_tables = $('table.'+users_table_class).each(function(){
            if (!$.fn.DataTable.isDataTable($(this))) {
                var datatable = $($(this)).DataTable({
                    "language": {
                        "emptyTable": 'There are no Users to show!'
                    },
                    "pageLength": 25,
                    // "deferRender": true,
                    responsive: {
                        details: {
                            display: $.fn.dataTable.Responsive.display.childRow,
                            type: 'column'
                        }
                    },
                    columnDefs: [
                        {
                            className: 'control',
                            orderable: false,
                            targets: 0
                        }
                    ],
                    "order": [[3, "desc"]],
                    "orderClasses": false
                });

                // datatable.on( 'responsive-display', function ( e, datatable, row, showHide, update ) {
                //     // responsive-display: when the hidden row are shown/hide either by user or automatically
                //     console.log( 'Details for row '+row.index()+' '+(showHide ? 'shown' : 'hidden') + 'update:' + update );
                //     datatable.columns.adjust();
                //     datatable.responsive.recalc();
                // } );

                // datatable.on( 'responsive-resize', function ( e, table, columns ) {
                // todo properly resize datatable. The problem is: you are in small screen, the table has hidden rows,
                // you go to full screen and the with of the table doesn't follow
                //     console.log("responsive-resize");
                //     table.columns.adjust().responsive.recalc().draw();
                // });

                datatable.on('order.dt', function() {
                    // In order events on the leader board table, the index column is recalculated. Not in search in order
                    // to be able to see the position of a user if you search for him
                    datatable.column(1, {order: 'applied'}).nodes().each(function (cell, i) {
                        cell.innerHTML = i + 1;
                    })
                }).draw();

                counter += 1;
                // notice that temp_id is not the tables id it is just a random string. But it doesn't matter.
                // All that we want is to take the datatable object when we iterate the in_tab_datatables
                // var temp_id = users_table_class + '_' + String(counter);
                // in_tab_datatables[temp_id] = datatable;  // the user list tables are not inside a tab
                other_datatables.push(datatable)
            }
        });

        var tbs_table_class = "tbs_table";
        var counter = 0;
        var users_tables = $('table.'+tbs_table_class).each(function(){
            if (!$.fn.DataTable.isDataTable($(this))) {
            var datatable = $($(this)).DataTable({
                "language": {
                    "emptyTable": 'There are no Bets to show!'
                },
                responsive: {
                    details: {
                        display: $.fn.dataTable.Responsive.display.childRow,
                        type: 'column'
                    }
                },
                columnDefs: [ {
                    className: 'control',
                    orderable: false,
                    targets:   0
                } ],
                //responsive: true,
                //"columnDefs": [
                //    { responsivePriority: 1, targets: 0 },
                //    { responsivePriority: 2, targets: -1 },
                //    {
                //        "render": function ( data, type, row ) {
                //            console.log('data: ',data);
                //            return Moment(data).format(date_format);
                //        },
                //        "targets": [1]
                //    }
                //],
                "order": [[3, "desc"]],
                "orderClasses": false
            });
            counter += 1;
            var temp_id = tbs_table_class + '_' + String(counter);
            in_tab_datatables[temp_id] = datatable;
            }
        });

        if (!$.fn.DataTable.isDataTable('#popular_bevs_datatable')) {
            $('#popular_bevs_datatable').DataTable({
                // "pageLength": 25,
                "language": {
                    "emptyTable": 'It seems that no one has submitted a bet yet...'
                },
                responsive: {
                    details: {
                        display: $.fn.dataTable.Responsive.display.childRow,
                        type: 'column'
                    }
                },
                columnDefs: [ {
                    className: 'control',
                    orderable: false,
                    targets:   0
                } ],
                "order": [[2, "desc"]],
                "orderClasses": false  // removes the default classes of the ordering column so the background color doesn't change
            });
        }

        if (!$.fn.DataTable.isDataTable('#latest_win_tbs_datatable')) {
            $('#latest_win_tbs_datatable').DataTable({
                responsive: {
                    details: {
                        display: $.fn.dataTable.Responsive.display.childRow,
                        type: 'column'
                    }
                },
                columnDefs: [ {
                    className: 'control',
                    orderable: false,
                    targets:   0
                } ],
                "order": [[6, "desc"]],
                "orderClasses": false  // removes the default classes of the ordering column so the background color doesn't change
            });
        }
    }

    function width_recalc() {
        // for (var i=0; i<other_datatables.length; i++){
        //     var datatable = other_datatables[i];
        //     datatable.columns.adjust();
        //     datatable.responsive.recalc();
        //     datatable.draw();
        // }
    }

    return{
        // width_recalc: width_recalc,
        get_data: get_data,
        init: init
    }
});