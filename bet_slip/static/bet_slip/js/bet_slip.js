/**
 * Created by xene on 9/18/2015.
 */

// TODO follow the method instructed in django docs, to automatically add the csrf tokken to all ajax post requests
// TODO Deprecation Notice: The jqXHR.success(), jqXHR.error(), and jqXHR.complete() callbacks are deprecated as of jQuery 1.8.
// To prepare your code for their eventual removal, use jqXHR.done(), jqXHR.fail(), and jqXHR.always() instead.

// Notice: there are 2 forms that are related with the bookmaker
// --
// form in bet_slip (in pages with bet_slip)
// html: games/bookmakers_list.html, form id: #bet_amount_form, field name: bookmaker_name, field id: id_bookmaker_name
// --
// form in options list button (in pages with events)
// html: bet_slip/place_bet_form.html, form id: #bookmakers_form, data-pjax, field name: selected_bookmaker_name, field id: selected_bookmaker_name_input
// --
// The session variable that stores the selected bookmaker is: selected_bookmaker_name
// place_bet --> returns: empty_bet_form (the bookmaker in session is updated from the bet_slip bookmaker form)
// change bookmaker selection option --> returns: planned_competitions or all_events (the bookmaker session is updated from the bookmakers_list form)
// but the bet_slip bookmaker form value isn't updated. I update it when you will press the place bet.
// I can update this field immediately after the bookmaker_list change.
//
// TODO HIGH BOOKMAKERS FORM is there a reason for keeping the bookmaker form in the bet slip? Only if there is a case in which the bookmaker in session
// is not updated, is not in sync with the bookmaker of the options list.
// I think the only reason to have a bookmaker in bet_slip was to be able to send the bookmaker in place_bet action from a page that has no bookmakers list.
// In this case you send the bookmaker from the bet_slip form. But there is no need to send a bookmaker. You can get the bookmaker from the session
// when you place bet (not from the bet_slip form). The session is updated every time you select a bookmaker from the list (and when you place a bet).
// So the session will be updated when you will use it to place a bet. Check also for pjax and back/forward if there is any other reason.

define([
    'jquery',
    'js/utils',
    'bet_tagging/js/bet_tagging',
    'bootstrap_growl'
], function($, Utils, Bet_tagging){

    var config = {
        debug: Utils.config.logger.bet_slip,
        form_wrapper: '#place_bet_form_wrapper',
        form_id: '#bet_amount_form',
        field_id: '#id_bookmaker_name',
        field_name: 'bookmaker_name',
        bet_amount_id: '#id_bet_amount',
        total_odd_el: "#total_bet_odd",
        place_bet_btn_id: 'place_bet',
        max_num_events: 14
    };

    var log = Utils.create_logger(config.debug);
    var form_id = config.form_id;
    var field_id = config.field_id;
    var bet_amount_id = config.bet_amount_id;
    // A list of objects. Each object represents a bet_slip item. An object is created when a new bet_slip item is added
    // and is removed when an item is removed.
    var bet_slip_items_list = [];
    var form_wrapper = config.form_wrapper;
    var total_odd_el = config.total_odd_el;
    var total_odd = 1.;
    var place_bet_btn_ladda = null;

    function bind_events(){
        $(document).on("click", 'button.market_option', function(){
            add_to_bet_slip($(this));
        });

        $(document).on("click", '.remove_from_bet_slip', function(){
            // the buttons with class "remove_from_bet_slip" are added to the DOM with jquery and ajax, so in order to add handlers
            // to them, we use the selector argument of the on method. We attach the method on a parent element and define the child
            // selector which in this case is the "remove_from_bet_slip" class
            var bet_items = [];
            bet_items.push($(this).closest('.bet_slip_item'));
            remove_items_from_bet_slip(bet_items);
        });

        $(document).on('submit', form_id, function(event){
            // uncomment to make the AJAX call a normal POST request for debugging purposes
            //var bookmaker_name = $('#bookmakers_button').text().trim();
            //// put the bookmaker name in the respective form's hidden field
            //if (bookmaker_name){
            //    $(this).find(field_id).val(bookmaker_name);
            //}
            event.preventDefault();
            var button = document.getElementById(config.place_bet_btn_id);
            place_bet_btn_ladda = Utils.toggle_ladda_spin(null, button);
            place_bet($(this));
        });

        $(document).on('items_to_bet_slip', function(){
            // using jquery-ui effect method
            $('.dropdown-quick-sidebar-toggler a').effect("highlight", {color: '#348bd2'}, 2000);
        });
    }

    function bet_allowed(){
        //Bet_tagging.bet_tag_balance_check();
    }

    function create_bet_slip_item_obj(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team){
        var bet_slip_item_obj = {};
        bet_slip_item_obj.event_id = event_id;
        bet_slip_item_obj.market_type_id = market_type_id;
        bet_slip_item_obj.choice = choice;
        bet_slip_item_obj.original_odd = original_odd;
        bet_slip_item_obj.selected_button_text = selected_button_text;
        bet_slip_item_obj.home_team = home_team;
        bet_slip_item_obj.away_team = away_team;
        return bet_slip_item_obj
    }

    function bet_slip_obj_in_list(bet_slip_items_list, event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team){
        //var index = bet_slip_items_list.findIndex(item => item.market_type_id==market_type_id);
        if (bet_slip_items_list.length) {
            for (var i = 0; i < bet_slip_items_list.length; i++) {
                if (
                    bet_slip_items_list[i].event_id == event_id &&
                    bet_slip_items_list[i].market_type_id == market_type_id &&
                    bet_slip_items_list[i].choice == choice &&
                    bet_slip_items_list[i].original_odd == original_odd &&
                    bet_slip_items_list[i].selected_button_text == selected_button_text &&
                    bet_slip_items_list[i].home_team == home_team &&
                    bet_slip_items_list[i].away_team == away_team
                ) {
                    return {in_index: i}
                }
            }
        }
        return false
    }

    function remove_bet_slip_item_obj_from_list(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team) {
        var found = bet_slip_obj_in_list(bet_slip_items_list, event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team);
        if (found){
            var removed_item = bet_slip_items_list.splice(found.in_index, 1);
            log("item removed", removed_item);
        }
    }

    function create_bet_slip_item(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team){
        // We add the session variables in the id of the item because the remove item from basket js function takes this values
        // from the id, sends it to the server and if the selected item is in the session, is deleted.

        var home_team_presentation = id_to_original_string(home_team);
        var away_team_presentation = id_to_original_string(away_team);
        var selected_button_text_presentation = id_to_original_string(selected_button_text);
        var bet_slip_item_id = String(event_id)+"--"+String(market_type_id)+"--"+String(choice)+"--"+String(original_odd)+"--"+
            String(selected_button_text)+"--"+String(home_team)+"--"+String(away_team);

        //var odd_part = '<div class="odd col-sm-2">'+original_odd.toFixed(2)+'</div>';
        //var button_div = '<div class="col-sm-2"><button type="button" class="close remove_from_bet_slip" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>';
        //var rest_part = '<div class="col-sm-8">' + home_team+"-"+away_team+": "+selected_button_text+'</div>';
        //var bet_item_text = '<div class="row">'+rest_part + odd_part + button_div +'</div>';
        //$('<div class="col-sm-12 well well-sm bet_slip_item"></div>').appendTo('#bet_slip_events_list').attr("id", bet_slip_item_id).append(bet_item_text);

        var head = '<h4 class="media-heading">'+ selected_button_text_presentation + '<span class="odd">'+ original_odd.toFixed(2) +'</span>' +'</h4>';
        var sub_head = '<div class="media-heading-sub">'+ home_team_presentation+"-"+away_team_presentation +'</div>';
        var button_div = '<div class="media-status"><button type="button" class="btn remove_from_bet_slip" aria-label="Close"><span class="glyphicon glyphicon-remove"></span></button></div>';
        //var button_div = '<a href="#" class="close"></a>';
        var bet_item_text = '<div class="media-body">'+ button_div + head + sub_head + '</div>';
        $('<li class="media bet_slip_item"></li>').appendTo('#bet_slip_events_list').attr("id", bet_slip_item_id).append(bet_item_text);
    }

    function create_bet_slip_items_from_json(json_array){
        log("creating bet slip items from data...");
        $('#bet_slip_events_list').empty();
        bet_slip_items_list = [];
        for (var i = 0; i < json_array.length; i++){
            var json_object = json_array[i];
            if (json_object){
                var event_id = json_object.event_id;
                var market_type_id = json_object.market_type_id;
                var choice = json_object.choice;
                var original_odd = json_object.original_odd;
                var selected_button_text = json_object.selected_button_text;
                var home_team = json_object.home_team;
                var away_team = json_object.away_team;
                create_bet_slip_item(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team);

                var bet_slip_item_obj = create_bet_slip_item_obj(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team);
                bet_slip_items_list.push(bet_slip_item_obj);
            }
        }
        calc_total_odd('create', null);
        if (json_array.length){
            $(document).trigger('items_to_bet_slip')
        }
    }

    function serve_initial_bet_form(){
        // The form is in a separate html file so it needs to be "manually" loaded whenever the document is ready
        // I put it in a separate file because I wanted to use a django form for it.
        // TODO low bet_slip probably serving the initial form is a not necessary server call? But its necessary now for back/for buttons
        log('serving initial bet form...');
        $.ajax({
            url: window.location.pathname+'PlaceBet/',
            type: 'GET',
            datatype: 'html',

            success: function (data, status, xhr) {
                log("serve_initial_bet_form: Bet form data received");
                $(form_wrapper).append(data);
            },
            error: function(data) {
                var message = 'AJAX Error. Initial bet form not loaded.';
                log(data, message);
            }
        });
    }

    function get_bet_slip(){
        log("getting bet slip...");
        $.ajax({
            url: window.location.pathname+'GetBetSlip/',
            type: 'GET',
            datatype: 'json',

            success: function (data, status, xhr) {
                log("bet slip data received");
                //log("status: ",status, " xhr: ", xhr);
                //log("data: ",data);
                //$('#bet_slip_events_list').append(data);
                create_bet_slip_items_from_json(data)
            },
            error: function(data) {
                var message = "Error on AJAX, bet slip not loaded";
                log(data, message);
            }
        });
    }

    function get_selected_odd($pressed_btn){
        var odd_input = $pressed_btn.closest('div.market_spinner_wrapper').find('.spinner').find('input');
        var odd = odd_input.val();
        var min_odd = odd_input.attr('min');
        var max_odd = odd_input.attr('max');
        log("odd: ", odd, "min", min_odd, "max", max_odd);
        return {"selected_odd": odd, "min_odd": min_odd, "max_odd": max_odd}
    }

    function is_odd_allowed(selected_odd, min_odd, max_odd){
        if (parseFloat(selected_odd) <= 1){ return }
        if (parseFloat(selected_odd) < parseFloat(min_odd) || parseFloat(selected_odd) > parseFloat(max_odd)){
            return
        }
        return true
    }

    function are_values_valid(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team){
        log("event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team");
        log(event_id, market_type_id, choice, original_odd, selected_button_text, home_team, away_team);
        if (!event_id || !market_type_id || !choice || !original_odd || !selected_button_text || !home_team || !away_team){
            return
        }
        return true
    }

    function original_to_id_string(value){
        // I store these values to the del from bet slip button id. On remove from bet slip these values are taken
        // from the id and are removed from the session. It's better that the id has no empty spaces. So I "encode"
        // them. Later if I want to use these values for presentation purposes I must "decode" them.
        // These values must be stored "encoded" in the session in order to be removed from the session.
        // TODO data-attr replace this stupid thing with data attributes
        if (value.indexOf('__') != -1){
            // if the original string has an existing __ it must be stored so not to be decoded to empty later
            log('__ exists in string')
        }
        var modified_value = value.split(' ').join('__');
        return modified_value
    }

    function id_to_original_string(value){
        var modified_value = value.split('__').join(' ');
        return modified_value
    }

    function event_in_bet_slip(bet_slip_items_list, event_id) {
        //var index = bet_slip_items_list.findIndex(item => item.event_id==event_id);
        var result = bet_slip_items_list.filter(function( obj ) {
            return obj.event_id === event_id;
        });
        if (result.length) {
            return true
        }
    }

    function max_num_events_reached(bet_slip_items_list){
        return bet_slip_items_list.length >= config.max_num_events
    }

    function add_to_bet_slip($this) {
        // Any value that we want to show in a item in the bet slip, must also be stored in the session. This because the bet
        // slip reloads in every page reload and it is re-created again from the session values. The same values must also be
        // in the id of the dom element of the bet slip item, since the remove from bet slip js function takes these values
        // from the id and sends them to the server. If the selected item is in the session, it will be removed.
        // Notice: We remove the empty spaces from the values before we send them to the server.
        var event_id = $this.closest('li.event_list_item').attr('id');
        event_id = event_id.split('_')[1];
        var market_type_classes = $this.closest('div.btn-group').attr('class');
        var market_type_class = market_type_classes.split(' ')[1];
        var market_type_id = market_type_class.split('_')[1];
        var choice_classes = $this.attr('class');
        // Notice: the choice is the selection.choice which is the marketType result choices
        var choice = choice_classes.split(' ')[3];
        //var original_odd = $this.find('span.odd_wrapper').html();
        var res = get_selected_odd($this);
        var selected_odd = res['selected_odd'];
        //var selected_button_text = $this.find('span.option_wrapper').html().replace(' ', '').split(' ').join('');
        var selected_button_text = $this.find('span.option_wrapper').html();
        selected_button_text = original_to_id_string(selected_button_text);
        var btn_group = $this.closest('div.winner_wrapper');
        //log("btn_group",btn_group);
        //In all markets template I have the selected button is not a child of winner_wrapper so I have to select the winner
        //wrapper of the page (not a parent div). There is only one winner_wrapper in all_markets so it is ok
        if (typeof btn_group[0] === 'undefined'){
            //log("btn_group (is undefined)",btn_group);
            btn_group = $('div.winner_wrapper');
        }

        //the replace replaces initial empty space if present, and the split and join replaces all empty spaces
        //var home_team = btn_group.find('span.home_team').html().replace(' ', '').split(' ').join('');
        //var away_team = btn_group.find('span.away_team').html().replace(' ', '').split(' ').join('');
        var home_team = btn_group.find('span.home_team').html();
        home_team = original_to_id_string(home_team);
        var away_team = btn_group.find('span.away_team').html();
        away_team = original_to_id_string(away_team);

        var odd_allowed = is_odd_allowed(selected_odd, res["min_odd"], res["max_odd"]);
        var valid_values = are_values_valid(event_id, market_type_id, choice, selected_odd, selected_button_text, home_team, away_team);

        if (!odd_allowed){
            var message = "No odds available yet!";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            return
        }
        if (event_in_bet_slip(bet_slip_items_list, event_id)){
            var message = "Event is already in bet slip!";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            return
        }
        if (max_num_events_reached(bet_slip_items_list)){
            var message = "The maximum number of bets has been reached!";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            return
        }
        if (!valid_values){
            var message = "An error occurred please reload the page and try again!";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            return
        }
        var current_url = window.location.pathname;
        var function_specific_url = 'AddToBetSlip/';
        var ajax_url = current_url+function_specific_url;
        //var ajax_url = current_url;
        //if (current_url.indexOf(function_specific_url) == -1) {ajax_url = ajax_url + function_specific_url;}
        $.ajax({
            url: ajax_url,
            type: 'POST',
            datatype: 'json',
            //datatype: 'html',
            data: {
                event_id: event_id,
                market_type_id: market_type_id,
                choice: choice,
                selected_odd: selected_odd,
                selected_button_text: selected_button_text,
                home_team: home_team,
                away_team: away_team,
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function (data, status, xhr) {
                log("data from add to bet slip ",data);
                create_bet_slip_items_from_json(data);
                var message = "Added to Bet Slip!";
                $.bootstrapGrowl(message, {type: 'success', align: 'center', delay: '1500'});
                //$('#bet_slip_events_list').empty().append(data);

                //conflict_message = "This option can't be added to bet slip. There is a conflict with another option"
                //history.pushState(null, null, current_url);
                //if (current_url.indexOf(function_specific_url) == -1){history.pushState(null, null, ajax_url);}
            },
            error: function(data) {
                var message = "Error on AJAX. Please reload the page and try again!";
                log(data, message);
                $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            }
        });
    }

    function get_data_list(items){
        /**
        * @items a js array of list items or a jquery object array with list items
        * @return a list of objects. Each object contains the bet slip item data
        */
        if(!items){return}
        var data_list = [];
        $.each(items, function(){
            var item = $(this);
            var del_button_div = item.attr('id');
            var item_data = {};
            item_data.event_id = del_button_div.split('--')[0];
            item_data.market_type_id = del_button_div.split('--')[1];
            item_data.choice = del_button_div.split('--')[2];
            item_data.original_odd = del_button_div.split('--')[3];
            item_data.selected_button_text = del_button_div.split('--')[4];
            item_data.home_team = del_button_div.split('--')[5];
            item_data.away_team = del_button_div.split('--')[6];
            data_list.push(item_data)
        });
        return data_list
    }

    function remove_items_from_bet_slip(items){
        // items is a js array of list items or a jquery object array with list items
        var data_list = get_data_list(items);
        if (!data_list){return}
        var json_data_list = JSON.stringify(data_list);
        $.ajax({
            url: window.location.pathname+'RemoveFromBetSlip/',
            type: 'POST',
            datatype: 'html',
            data: {
                data_list: json_data_list,
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },

            success: function (data, status, xhr) {
                $.each(items, function () {
                    var item = $(this);
                    item.hide("slow", function(){item.remove();});
                });
                data_list.forEach(function (item_data) {
                    remove_bet_slip_item_obj_from_list(item_data.event_id, item_data.market_type_id, item_data.choice,
                        item_data.original_odd, item_data.selected_button_text, item_data.home_team, item_data.away_team);
                    calc_total_odd('remove', item_data.original_odd);
                })
            },

            error: function(data) {
                var message = "Error on AJAX. Please reload the page and try again!";
                log(data, message);
                $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            }

        });
    }

    function place_bet($this){
        // The bet slip values will be read from the session (which is written from the add_to_bet_slip action) so there is no
        // need to send them in the AJAX request
        log('Submitting bet...');
        // form with id --> form_id
        var form = $this;
        // We take the value from the bookmakers_list and add it to bet_slips hidden bookmaker_name form field.
        // TODO HIGH BOOKMAKERS FORM Has this any meaning?
        // Notice that some pages might not have the bookmakers list. In this case the bet_slip bookmaker will not be updated
        // from the bookmakers list and will be its default value. The default value is the one returned from the
        // empty_bet_form view which is the session bookmaker or the default one.
        var bookmaker_list_name = $('#bookmakers_button').text().trim();
        log('bookmaker_list_name', bookmaker_list_name);

        // We use the default ids that django creates for the input fields of its forms
        var bet_slip_bookmaker_field_id = field_id;
        var bet_slip_bet_amount_id = bet_amount_id;
        if (bookmaker_list_name){
            form.find(bet_slip_bookmaker_field_id).val(bookmaker_list_name);
        }

        var bet_amount = form.find(bet_slip_bet_amount_id).val();

        var bet_tag_ids = JSON.stringify(Bet_tagging.selected_bet_tags()['selected_tag_ids']);
        var jsoned_bet_description = Bet_tagging.get_bet_description();

        var url_obj = Bet_tagging.get_bet_description_url_obj();
        var jsoned_bet_description_url = url_obj["url"];
        var is_valid_url = url_obj["is_valid"];
        if (!is_valid_url){
            var message = "Please define a valid description url";
            $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
            Utils.toggle_ladda_spin(place_bet_btn_ladda);
            return;
        }

        $.ajax({
            type: 'POST',
            url: window.location.pathname+'PlaceBet/',
            datatype: 'html',
            //url: form.attr('action'),
            //data: form.serialize(),
            data:{
                bet_amount: bet_amount,
                bookmaker_name:  form.find(bet_slip_bookmaker_field_id).val(),
                selected_bet_tag_ids: bet_tag_ids,
                bet_description: jsoned_bet_description,
                bet_description_url: jsoned_bet_description_url,
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function (data, status, xhr) {
                //$(document).trigger('bet_submitted', [bet_amount]);  # you can pass also data if you want
                $(document).trigger('bet_submitted');
                $(form_wrapper).html(data);
                Utils.create_messages();

                try{var keep_selections = $('#keep_selections').find("input").is(":checked");}catch(e) {var keep_selections = false;}
                if (!keep_selections){
                    // var saved_successfully = $("#total_bet_saved_successfully").data("saved_successully");
                    // console.log('keep:', keep_selections);
                    var saved_successfully = $("#total_bet_saved_successfully").attr("data-saved_successully");
                    // console.log("saved", saved_successfully);
                    if (saved_successfully === "True") {
                        var items = $('#bet_slip_events_list').find('li.bet_slip_item');
                        remove_items_from_bet_slip(items);
                    }
                }
                Utils.toggle_ladda_spin(place_bet_btn_ladda);
            },
            error: function(data) {
                var message = "Error on AJAX";
                if(data.responseText.indexOf('Error') > -1){
                    message = "Bet isn't saved! Error on AJAX"
                }
                $.bootstrapGrowl(message, {type: 'danger', align: 'center'});
                Utils.toggle_ladda_spin(place_bet_btn_ladda);
            }
        });
    }

    function calc_total_odd(method, odd){
        log("calculating total odd...");
        if (method === 'create'){
            total_odd = 1;
            for (var i=0; i<bet_slip_items_list.length; i++){
                total_odd = total_odd * bet_slip_items_list[i].original_odd;
            }
        }else{
            odd = parseFloat(odd);
            total_odd = total_odd/odd;
        }
        $(total_odd_el).html(total_odd.toFixed(2));
    }

    return {
        bind_events: bind_events,
        serve_initial_bet_form: serve_initial_bet_form,
        get_bet_slip: get_bet_slip
    }
});



