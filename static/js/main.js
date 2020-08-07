/**
 * Created by xene on 4/26/2016.
 */

requirejs.config({
    // TODO HIGH delete the baseUrl. files will be located relative to the main.js. This means that I need to remove
    // the js (from js/app -> app, js/router -> router etc.)
    // baseUrl: "/static/",
    baseUrl: "https://s3.eu-central-1.amazonaws.com/zakanda-static-01/static/",
    paths: {
        jquery: "https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min",
        getstream: "js/libs/getstream",
        colorbrewer: "js/libs/colorbrewer",
        jquery_ui: "metronic/assets/global/plugins/jquery-ui/jquery-ui.min",
        bootstrap: "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min",
        // bootstrap: "js/libs/bootstrap.min",
        d3: "https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.12/d3",
        //d3: "js/libs/d3.min",
        //crossfilter: "https://cdnjs.cloudflare.com/ajax/libs/crossfilter/1.3.12/crossfilter",
        crossfilter: "js/libs/crossfilter", // 1.4.0(alpha 6)
        //dc: "http://dc-js.github.io/dc.js/js/dc",
        //'dc': "http://cdnjs.cloudflare.com/ajax/libs/dc/1.7.5/dc"
        //dc: "https://cdnjs.cloudflare.com/ajax/libs/dc/2.0.0/dc.min",  // worked ok
        dc: "https://cdnjs.cloudflare.com/ajax/libs/dc/2.1.3/dc.min",

        // Important: The name 'datatables.net' is required by the datatables_responsive so I name it like this
        'datatables.net': "https://cdn.datatables.net/1.10.12/js/jquery.dataTables.min",
        // moment_timezone: "https://cdnjs.cloudflare.com/ajax/libs/moment-timezone/0.5.13/moment-timezone.min",
        moment: "https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.18.1/moment.min",
        //bootstrap_switch: "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-switch/3.3.2/js/bootstrap-switch.min",
        bootstrap_switch: "metronic/assets/global/plugins/bootstrap-switch/js/bootstrap-switch.min",
        ladda: "metronic/assets/global/plugins/ladda/ladda.min",
        spin: "metronic/assets/global/plugins/ladda/spin.min",
        //select2: "https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.3/js/select2.min",
        select2: "metronic/assets/global/plugins/select2/js/select2.min",
        jasny_bootstrap: "js/libs/jasny_bootstrap",

        //cookie: "metronic/assets/global/plugins/js.cookie",  // it's loaded normally since the global Cookies is used
        blockui: "metronic/assets/global/plugins/jquery.blockui.min",
        slimscroll: "metronic/assets/global/plugins/jquery-slimscroll/jquery.slimscroll",
        // the following scripts have been slightly modified (see last lines). The call on their init is done in my init.js
        metronic_app: "metronic/assets/global/scripts/app",
        layout: "js/metronic_custom/layout",
        demo: "metronic/assets/layouts/layout/scripts/demo",
        quick_sidebar: "metronic/assets/layouts/global/scripts/quick-sidebar",
        quick_nav: "metronic/assets/layouts/global/scripts/quick-nav",
        datatables_responsive: "https://cdn.datatables.net/responsive/2.1.0/js/dataTables.responsive.min",
        bootstrap_growl: "metronic/assets/global/plugins/bootstrap-growl/jquery.bootstrap-growl.min"
        // boostrapDatePicker: "metronic/assets/global/plugins/bootstrap-daterangepicker/daterangepicker"  // not currently used
    },
    shim: {
        'dc': {deps: ['d3', 'crossfilter']},
        'crossfilter': {exports: 'crossfilter'},
        'metronic_app': {exports: 'App'},
        'layout': {deps: ['metronic_app'], exports: 'Layout'},
        // TODO on pjax updates of page-content I must follow the ajaxify process of the template, to re-initiate the
        // new content. I don't use it as is since I make pjax calls not ajax as it does. So copy on ajaxify event
        // handler actions before the ajax call, and on pjax success/failure execute the ajaxify success/failure
        // http://keenthemes.com/preview/metronic/theme/admin_1/layout_ajax_page.html
        'demo': {deps: ['metronic_app', 'layout'], exports: 'Demo'},
        'quick_sidebar': {exports: 'QuickSidebar'},
        'quick_nav': {exports: 'QuickNav'},
        // 'jquery_ui': {deps: ['jquery']},
        'bootstrap' : {deps: ['jquery', 'jquery_ui']},
        // 'moment': {deps: ['moment_timezone']},
        'jasny_bootstrap': {deps: ['jquery']},
        'datatables.net': {deps: ['jquery']},
        'datatables_responsive': {deps: ['datatables.net']},
        'select2': {deps: ['jquery']},
        'blockui': {deps: ['jquery']},
        'slimscroll': {deps: ['jquery']},
        'bootstrap_growl': {deps: ['jquery', 'bootstrap']},
        'bootstrap_switch': {deps: ['bootstrap']}
        // 'boostrapDatePicker': {
        //     deps: ['jquery', 'moment', 'bootstrap']
        //     // exports: "$.fn.datepicker"
        // }
    }
});

requirejs(['js/app']);