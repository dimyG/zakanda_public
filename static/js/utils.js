/**
 * Created by xene on 4/8/2016.
 */

define([
    'jquery',
    'js/urls',
    'moment',
    'ladda',
    'bootstrap_growl'
    // 'boostrapDatePicker'
], function($, Urls, Moment, Ladda){

    var config = {
        logger:{
            global: false,
            bet_slip: false,
            bet_statistics: false,
            feeds: false,
            games: false,
            user_accounts: false,
            router: false,
            init: false,
            utils: false
        },
        status:{
            Open: "Open",
            Won: "Won",
            Lost: "Lost",
            Void: "Void"
        },
        status_class:{
            won: "row_won",
            lost: "row_lost",
            void: "row_void"
        },
        session:{
            bet_tag: 'active_bet_tag_id'
        },
        normalization_methods: {
            unit: "Unit",
            percent: "Percent"
        },
        growl_settings: {
            ele: 'body', // which element to append to
            type: 'info', // (null, 'info', 'danger', 'success')
            offset: {from: 'top', amount: 20}, // 'top', or 'bottom'
            align: 'center', // ('left', 'right', or 'center')
            width: 250, // (integer, or 'auto')
            delay: 3000, // Time while the message will be displayed. It's not equivalent to the *demo* timeOut!
            allow_dismiss: true, // If true then will display a cross to close the popup.
            stackup_spacing: 10 // spacing between consecutively stacked growls.
        },
        main_container: '#main_container',
        left_sidebar_container: '#left_sidebar_container',
        left_and_main_container: '#left_and_main_container',
        sports_list_class: 'sports_list',
        user_info_class: 'user_info'
    };

    var log = create_logger(config.logger.utils);
    var global_debug = config.logger.global;
    var misc_data_url = Urls.gutils.misc_data;
    var main_container = config.main_container;
    var misc_data = {};
    var datatables = {};

    function create_messages(){
        $(".messages").find('.alert').each(function(){
            if ($(this).data('shown') === false){
                var message = $(this).find('.message').text();
                var message_tag = $(this).find('.message_tag').text();
                // bootstrapGrowl doesn't support warning and debug types
                if (message_tag === 'warning' || message_tag === 'debug'){message_tag = 'danger'}
                // bootstrapGrowl creates a message div and appends it to body by default
                $.bootstrapGrowl(message, {type: message_tag, align: 'center'});
                $(this).data('shown', 'true');
            }
        });
    }

    function update_screen_size_related_elements(){
        // console.log('window.width ', $(window).width());
        if ( $(window).width() > 991) {
            var portlets = $('div.portlet.collapsed_md_down');
            if (!portlets){return}
            portlets.each(function () {
                $(this).find('div.portlet-title>div.tools>a').removeClass('expand').addClass('collapse');
                $(this).find('div.portlet-body').removeClass('portlet-collapsed');
            })
        }else {

        }
    }

    function toggle_ladda_spin(ladda_instance, button){
        // button must be a javascript object not a jquery one
        // if a ladda instance is given then it will be toggled. If no ladda instance is given
        // then a new instance will be created from the given button and will be toggled
        ladda_instance = (typeof ladda_instance !== 'undefined') ?  ladda_instance : null;
        // button_id = (typeof button_id !== 'undefined') ?  button_id : null;

        if (!ladda_instance){
           // create a ladda instance for the given button id
            try{
                // var button = document.getElementById(button_id);
                ladda_instance = Ladda.create( button );
            }catch(error){
                log('unable to create ladda instance');
                return
            }
        }
        log('ladda instance: ', ladda_instance);
        ladda_instance.toggle();
        return ladda_instance
    }

     function QS(){
        // class that gets, adds and removes querystring parameters
        this.qs = {};
        //console.log('location.search: ', location.search);
        var s = location.search.replace( /^\?|#.*$/g, '' );
        //console.log('s: ', s);
        if( s ) {
            var qsParts = s.split('&');
            var i, nv;
            for (i = 0; i < qsParts.length; i++) {
                nv = qsParts[i].split('=');
                // decoding so that unicode strings like greek bet group names are decoded
                // so the array of bytes becomes a string
                this.qs[decodeURIComponent(nv[0])] = decodeURIComponent(nv[1]);
                // this.qs[nv[0]] = nv[1];
            }
            // console.log('qs (QS.qs): ', this.qs)
        }
    }
    QS.prototype.add = function( name, value ) {
        if( arguments.length == 1 && arguments[0].constructor == Object ) {
            this.addMany( arguments[0] );
            return;
        }
        this.qs[name] = value;
    };
    QS.prototype.addMany = function( newValues ) {
        for( nv in newValues ) {
            this.qs[nv] = newValues[nv];
        }
    };
    QS.prototype.remove = function( name ) {
        if( arguments.length == 1 && arguments[0].constructor == Array ) {
            this.removeMany( arguments[0] );
            return;
        }
        delete this.qs[name];
    };
    QS.prototype.removeMany = function( deleteNames ) {
        var i;
        for( i = 0; i < deleteNames.length; i++ ) {
            delete this.qs[deleteNames[i]];
        }
    };
    QS.prototype.getQueryString = function() {
        var nv, q = [];
        for( nv in this.qs ) {
            q[q.length] = nv+'='+this.qs[nv];
        }
        return q.join( '&' );
    };
    QS.prototype.toString = QS.prototype.getQueryString;

    function update_qs_params(key, value){
        log("updating querystring parameter " + key + "with value " + value + "...");
        var qs = new QS();
        qs.remove(key);
        qs.add(key, value);
        // pjax doesn't work if you manually affect the state (with pushState or replaceState). As a workaround
        // we use the $.pjax.state
        history.replaceState($.pjax.state, null, "?" + qs.toString());
    }

    var default_start_date = Moment();
    var default_end_date = Moment().add(7, 'days');
    var start_date = default_start_date;
    var end_date = default_end_date;

    function update_dates(start, end) {
        /** the dates contain also timezone info extracted probably from the OS. The tz is contained in the iso
         * format and so it is read in the server. */
        // formats the date to iso, and encodes it (so that the + sign is passed to the server)
        update_qs_params('end', encodeURIComponent(end.format()));
        update_qs_params('start', encodeURIComponent(start.format()));
        start_date = start;
        end_date = end;
        $.pjax.reload(main_container);
        // $('#date_range_picker span').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
    }

    function update_date_picker_html() {
        $('#date_range_picker span').html(start_date.format('MMMM D, YYYY') + ' - ' + end_date.format('MMMM D, YYYY'));
        start_date = default_start_date;
        end_date = default_end_date;
    }

    function init(){
        create_messages();

        // $('[data-toggle="tooltip"]').tooltip({html: true});  // doesn't work for some reason

        // $(function () {
        //     console.log($('[data-toggle="tooltip"]').attr("data-original-title"));
        //     $("body").tooltip({
        //         selector: '[data-toggle="tooltip"]',
        //         content: function(){
        //             console.log("TOOLTIP content function");
        //             var element = $( this );
        //             console.log("this", element);
        //             console.log(element.attr('title'));
        //             return element.attr("data-original-title")
        //         }
        //     });
        // })

        // $('#date_range_picker').daterangepicker(
        //     {
        //         // timePicker: true,
        //         // timePickerIncrement: 30,
        //         locale: {
        //             format: 'MM/DD/YYYY' // h:mm A
        //         },
        //         startDate: start_date,
        //         endDate: end_date,
        //         ranges: {
        //             // 'Next 24 hours': [Moment(), Moment().add(2, 'days')],
        //             'Today': [Moment(), Moment()],
        //             'Tomorrow': [Moment().add(1, 'days'), Moment().add(1, 'days')],
        //             'Day after Tomorrow': [Moment().add(2, 'days'), Moment().add(2, 'days')],
        //             'Next 3 days': [Moment(), Moment().add(3, 'days')],
        //             'Next 7 days': [Moment(), Moment().add(7, 'days')]
        //             // 'Last 30 Days': [Moment().subtract(29, 'days'), Moment()],
        //             // 'This Month': [Moment().startOf('month'), Moment().endOf('month')],
        //             // 'Last Month': [Moment().subtract(1, 'month').startOf('month'), Moment().subtract(1, 'month').endOf('month')]
        //         }
        //     },
        //     update_dates  // start and end are the user selected dates
        //     // function(start, end, label) {
        //     //     alert("A new date range was chosen: " + start.format('YYYY-MM-DD') + ' to ' + end.format('YYYY-MM-DD'));
        //     // }
        // );
        //
        // // the html needs to be updated after the html is loaded (pjax or not) since the date picker html
        // // is part of the main container :( This is done here in the init function (which is called after pjax
        // // or normal page load)
        // update_date_picker_html();
    }

    function indexOfMax(arr) {
        if (arr.length === 0) {
            return [-1, null];
        }

        var max = arr[0];
        var maxIndex = 0;

        for (var i = 1; i < arr.length; i++) {
            if (arr[i] > max) {
                maxIndex = i;
                max = arr[i];
            }
        }

        return [maxIndex, max];
    }

    function create_logger(debug){
        var log_obj = {};
        log_obj.debug = debug;
        log_obj.evaluate_log = function(){
            if (log_obj.debug){
                log_obj.log = function(){
                    for (var i=0; i<arguments.length; i++) console.log(arguments[i]);
                    return arguments;
                }
            }else{
                log_obj.log = function(input) {
                    return null
                }
            }
        };
        log_obj.evaluate_log();
        return log_obj.log
    }

    function update_session(key_value_pairs){
        // key_value_pairs: list of objects
        // TODO make all session updates through this function
        $.ajax({
            type: 'POST',
            url: Urls.gutils.update_session,
            datatype: 'json',
            data: {
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
                key_value_pairs: JSON.stringify(key_value_pairs)
            },
            success: function (json_data) {
                log(json_data);
            },
            error: function () {
                log("Warning: Ajax error, session wasn't updated");
            }
        })
    }

    function logger(){return create_logger(global_debug)} // a global logger object that uses the global debug

    function bind_events(){
        $(document).on("click", "a.competition_link, div.page-header a:not(.menu-toggler.responsive-toggler), div.user_info a", function () {
            /** Hides the left sidebar (in small screens) if the users clicks on these links */
            // if aria-expanded is true then the element is open
            if ($("#left_and_main_container > div.page-sidebar-wrapper > div").attr("aria-expanded")){
                $("#left_and_main_container > div.page-sidebar-wrapper > div").collapse('hide');
            }
            // $("a.menu-toggler.responsive-toggler").trigger("click");  // this is the link that opens closes
            // the left sidebar on small screens
        });
    }

    function get_misc_server_data(){
        misc_data.user_id = null;
        $.ajax({
            type: 'GET',
            url: misc_data_url,
            datatype: 'json',
            success: function (json_data) {
                log("misc server data received: ", json_data);
                if (json_data.user_id){
                    misc_data.user_id = json_data.user_id
                }else{
                    log("User is not logged in")
                }
            },
            error: function () {
                log('misc server data not received');
            }
        })
    }

    get_misc_server_data();  // so the data are always available

    function set_get_url_parameter(paramName, paramValue){
        var url = window.location.href;
        var hash = location.hash;
        url = url.replace(hash, '');
        if (url.indexOf(paramName + "=") >= 0)
        {
            var prefix = url.substring(0, url.indexOf(paramName));
            var suffix = url.substring(url.indexOf(paramName));
            suffix = suffix.substring(suffix.indexOf("=") + 1);
            suffix = (suffix.indexOf("&") >= 0) ? suffix.substring(suffix.indexOf("&")) : "";
            url = prefix + paramName + "=" + paramValue + suffix;
        }
        else
        {
        if (url.indexOf("?") < 0)
            url += "?" + paramName + "=" + paramValue;
        else
            url += "&" + paramName + "=" + paramValue;
        }
        window.location.href = url + hash;
    }

    function trim_value(value, max, min){
        if(value < min){
            value = min
        }else if( value > max){
            value = max
        }
        return value
    }

    function combine_groups() {
        // combines given crossfilter groups to one fake group (an object with an all method). The all method returns
        // the combined keys of all groups. The value of each key is an array with the values of each group (for this key)
        // if a key doesn't exists in a group, its group value in the result will be 0
        // [ {key: group_key, value: [group_1_value, group_2_value]}, {} ... {}  ]

        // groups is an array with the arguments [group1, group2, ... ]
        var groups = Array.prototype.slice.call(arguments);
        return {
            all: function() {
                // alls is the return of all() for each group, combined in one array
                // [ [{key: group1_key1, value: group1_val1}, {key: gr1_key2, value: gr2_val2}, ... ] , [ {key: gr2_key1, value: gr2_val1} ... ]
                var alls = groups.map(function(g) { return g.all(); });
                //console.debug('alls', alls);
                var gm = {};
                alls.forEach(function(a, i) {
                    //console.debug('a', a, 'i', i);
                    a.forEach(function(b) {
                        //console.debug('b', b);
                        if(!gm[b.key]) {
                            gm[b.key] = new Array(groups.length);
                            for(var j=0; j<groups.length; ++j)
                                gm[b.key][j] = 0;
                        }
                        gm[b.key][i] = b.value;
                        //console.log('gm', gm)
                    });
                });
                var ret = [];
                for(var k in gm)
                    // notice: the keys "k" are strings. You have to convert them to the type you want to use
                    // currently I do this by patching the all method when I want to use it
                    ret.push({key: k, value: gm[k]});
                return ret;
            }
        };
    }

    return {
        bind_events: bind_events,
        init: init,
        create_logger: create_logger,
        logger: logger,
        get_misc_server_data: get_misc_server_data,
        QS: QS,
        update_qs_params: update_qs_params,
        config: config,
        misc_data: misc_data,
        trim_value: trim_value,
        // Every datatable that lies inside a tab must be added to the datatables object, so it's width
        // is recalculated when the tab becomes visible.
        datatables: datatables,
        update_session: update_session,
        create_messages: create_messages,
        indexOfMax: indexOfMax,
        combine_groups: combine_groups,
        update_date_picker_html: update_date_picker_html,
        toggle_ladda_spin: toggle_ladda_spin,
        update_screen_size_related_elements: update_screen_size_related_elements
    }
});
