/**
 * Created by xene on 7/9/2016.
 */

define([
    'js/router',
    'js/utils',
    'js/urls',
    'jquery',
    'js/libs/getstream',
    'js/libs/jquery.pjax'
], function(Router, Utils, Urls, $, Stream){

    var config = {
        debug: Utils.config.logger.feeds,
        //debug: true,
        profile_dropdown_menu: "#profile_drop_down",
        notifications_span: "#notifications",
        notifications_link: "#notifications_wrapper",
        // zakanda
        stream_app_key: "ycrrhcg3h4k8",
        stream_app_id: '13238',
        stream_app_location: 'us-east',
        // zakanda_dev
        // stream_app_key: "p5wg5cf725j5",
        // stream_app_id: '21502',
        // stream_app_location: 'us-east',
        notification_feed_name: 'notification'
    };

    var log = Utils.create_logger(config.debug);
    var profile_menu = config.profile_dropdown_menu;
    var notifications_span = config.notifications_span;
    var notifications_link = config.notifications_link;
    var stream_user_data_url = Urls.stream.stream_user_data;
    var notification_feed_name = config.notification_feed_name;
    // it's used in order to know how many notification activities to mark as seen when the notifications link is
    // clicked. This number must be the same with the activities per page of the back end view
    var activities_per_page = 100;
    var user_id = null;
    var stream_user_token = null;

    //function is_user_logged_in(){
    //    return $(document).find(profile_menu)
    //}

    function update_notifications_number(){
        var unseen = parseInt($(notifications_span).text());
        var remaining = unseen - activities_per_page;
        if (remaining > 0){
            $(notifications_span).text(remaining);
        }else{
            $(notifications_span).text('');
        }
    }

    function bind_events(){
        $(document).on("click", notifications_link, function(){
            update_notifications_number()
        });
    }

    function on_notification_data_success(data){
        // This counts the number of unseen notifications. If 2 users bet on the same bev then this is one notification
        log("on_notification_data_success", data);
        if (data.hasOwnProperty('unseen')){
            $(notifications_span).text(data.unseen);
        }
    }

    function realtime_update(data){
        // notice that this counts the number of activities. Bev submit in this case.
        if(data.hasOwnProperty('new')){
            var len_new_activities = data.new.length;
            var current_num = parseInt($(notifications_span).text());
            if (isNaN(current_num)){current_num = 0}
            var new_num = current_num + len_new_activities;
            $(notifications_span).text(new_num);
        }
    }

    function subscribe_to_stream(user_id, stream_user_token){
        var client = Stream.connect(config.stream_app_key, null, config.stream_app_id, { location:  config.stream_app_location});
        var user_notifications = client.feed(notification_feed_name, user_id, stream_user_token);
        user_notifications.get({limit: 100})
            .then(function(data){
                log(' - from then function - ');
                // it runs the first time and contains the data contain unseen/unread count
                on_notification_data_success(data)
            })
            .catch(function(reason){
                log("ERROR: user's notification data wasn't received, reason: " + reason)
            });

        function callback(data) {
            log(' - from callback function - ');
            //it runs when new action is done, the format is the activity format
            realtime_update(data)
        }

        function successCallback() {
            log('now listening to changes in realtime ');
        }

        function failCallback(data) {
            log("something went wrong with Stream's websocket (or equivalent) data, check the console logs");
            log(data);
        }

        user_notifications.subscribe(callback).then(successCallback, failCallback);
    }

    function handle_logged_in_user(user_id, stream_user_token){
        if(user_id && stream_user_token){
            subscribe_to_stream(user_id, stream_user_token)
        }else if (!stream_user_token) {
            log("ERROR: stream token for logged in user hasn't been received!");
        }else{
            log("ERROR: user id and stream user token for logged in user haven't been received")
        }
    }

    function process_stream_user_data(data) {
        if (data.length) {
            user_id = data[0];
            stream_user_token = data[1];
            handle_logged_in_user(user_id, stream_user_token);
        }else{
            log("user is not logged in!")
        }
    }

    function listen_to_stream(){
        log("trying to subscribe to stream...");
        //if (is_user_logged_in()){
        $.ajax({
            url: stream_user_data_url,
            type: 'GET',
            datatype: 'json',
            success: function (data, status, xhr) {
                log("stream user data received");
                process_stream_user_data(data);
            },
            error: function(data) {
                var message = "Error on AJAX. Stream user data not received";
                log(data, message);
            }
        });
        //}
    }

    return {
        bind_events: bind_events,
        listen_to_stream: listen_to_stream
    }
});