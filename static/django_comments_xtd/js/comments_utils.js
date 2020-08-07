define([
    'jquery',
    'js/utils'
], function($, Utils){

    function show_message(event){
        var user_id = Utils.misc_data.user_id;
        if (!user_id) {
            event.preventDefault();
            event.stopPropagation();
            var message = 'You have to Login to give your feedback';
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
        }
    }

    function bind_events(){
        $(document).on('click', '.comment span>span>a', function (event) {
            show_message(event);
        });

        $(document).on('click', '.comment .pull-right a', function (event) {
        // $(document).on('comment_rendered', function (event) {
            show_message(event);
        })
    }

    return {
        bind_events: bind_events
    }
});