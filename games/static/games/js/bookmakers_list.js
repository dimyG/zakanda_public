/**
 * Created by xene on 12/3/2015.
 *
 */

// The bookmaker_list_form is submitted with custom pjax call because we want to "catch" the success of this form submission.
// In default pjax calls the pjax events are called from the container and not from the link that they fired. So in this
// case you can't tell if a pjax success event was from this form submission or from something else. With custom pjax you can use the .done
//
// In case the xhr object of the pjax:end event is null then the page has been loaded from the cache. In this case if the
// cached page has a bookmakers form, I make an ajax post request to update the bookmaker name in the session with the
// bookmaker name of the cached page

// TODO create urls for each bookmaker selection so the state would be bookmarkable shared etc

define([
    'js/utils',
    'bet_slip/js/bet_slip',
    'jquery',
    'js/libs/jquery.pjax'
], function(Utils, Bet_slip, $){

    var config = {
        debug: Utils.config.logger.games,
        // debug: true,
        form_link_button: ".dropdown-menu.bookmakers_list li a",
        form_id: '#bookmakers_form',
        field_name: 'selected_bookmaker_name',
        field_id: '#selected_bookmaker_name_input'
    };

    var log = Utils.create_logger(config.debug);
    var glog = Utils.logger();
    var main_container = Utils.config.main_container;
    var form_link = config.form_link_button;
    var form_id = config.form_id;
    var field_id = config.field_id;
    var field_name = config.field_name;

    function init() {

    }

    function bind_events(){
        $(document).on("click", form_link, function(event){
            log('bookmaker change');
            var bookmaker_name = $(this).text();
            Utils.update_qs_params('bookmaker', bookmaker_name);
            update_bookmaker_links(bookmaker_name);
            submit_the_form($(this)); // if pjax supported will be submitted with custom pjax submit
        });

        //      >>>>>>>>>>>>>>>> Spinner related <<<<<<<<<<<<<<<<<<<
        $(document).on('click', '.spinner .btn:first-of-type', function() {
            var btn = $(this);
            var input = btn.closest('.spinner').find('input');

            //var button_class = btn.closest('.spinner').data("target");
            //var odd_span = btn.closest('.spinner').closest('.btn-group').find("."+button_class).find(".odd_wrapper");

            if (input.attr('max') == undefined || parseFloat(input.val()) < parseFloat(input.attr('max'))) {
                var max_val = parseFloat(input.attr('max'));
                var input_val = (parseFloat(input.val()) + 0.1).toFixed(2);
                if (input.attr('max') && input_val > max_val){
                    input_val = max_val;
                }
                input.val(input_val);

                //var odd_val = (parseFloat(odd_span.html()) + 0.1).toFixed(2);
                //odd_span.html(odd_val);

            } else {
                btn.next("disabled", true);
            }
        });

        $(document).on('click', '.spinner .btn:last-of-type', function() {
          var btn = $(this);
          var input = btn.closest('.spinner').find('input');
          if (input.attr('min') == undefined || parseFloat(input.val()) > parseFloat(input.attr('min'))) {
              var min_val = parseFloat(input.attr('min'));
              var input_val = (parseFloat(input.val()) - 0.1).toFixed(2);
              if (input.attr('min') && input_val < min_val){
                  input_val = min_val;
              }
              input.val(input_val);
          } else {
            btn.prev("disabled", true);
          }
        });

        //    >>>>>>>>>>>>>>>> End Spinner related <<<<<<<<<<<<<<<<<<<

    }

    function update_bookmaker_links(name){
        log("updating bookmaker links...");
        // there are some links (pick bets, planned events) that have a bookmaker url get parameter.
        // This parameter takes its value from the session selected bookmaker name value. But it takes
        // this value only when the page is loaded. The problem is that when we change the selected bookmaker
        // we want the hrefs of these links to be updated also with the new bookmaker. This is done here.
        $("a.bookmaker_param").each(function (index) {
            var a_href = $(this).attr("href");
            // console.debug($(this).attr("href"));
            var regex = /([?|&]bookmaker=)[^\\&]+/;
            // regex explanation:  literally match the string "bookmaker=", followed by one or more things that are
            // not the query string parameter separator ("&"), and replace with the captured match (the $1 refers
            // to the captured text "bookmaker=") followed by the new value
            var match = a_href.match(regex);
            if (!match){
                // if by some error the bookmaker parameter value is empty
                regex = /([?|&]bookmaker=)/;
            }
            a_href = a_href.replace(regex, '$1' + name);
            $(this).attr("href", a_href);
            // console.debug($(this).attr("href"));
        })
    }

    function bind_pjax_events(){
        $(document).on('submit', form_id, function(event){
            log('form submitted');
            event.preventDefault();
            // this is a custom pjax call so I have to externally call get_bet_slip since the default pjax events don't catch this custom pjax
            // I hadn't defined any callback and it worked until a point in time :( Why is not very clear. Need to check it
            // in comparison with the update_bookmaker_name_in_session() function calls
            custom_pjax_submit($(this), Bet_slip.get_bet_slip);
        });
    }

    function custom_pjax_submit($this, callback){
        // todo is there any reason for this custom submit? Maybe just for not adding a history entry?
        var current_url = window.location.href;
        log("submitting to url: ", current_url);
        var form = $this;
        var form_url = form.attr("action");
        var type = form.attr("method");
        var input_name = field_name;
        var input_val = form.find(field_id).val();
        var data = {
            selected_bookmaker_name: input_val,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        };
        log('form url', form_url);
        log('data', data);
        // .done fires after pjax:success (which means that the page has been updated)
        $.pjax({
            url: current_url,
            type: type,
            container: main_container,
            data: data,
            push: false  // doesn't add history entry so the back leads to the previous page, not to the previous bookmaker
        }).done(function() {
            log('Custom pjax done. Bookmakers list form submitted with pjax (fired after pjax:success)');
            //log("Calling ", callback, " ...");
            if (callback){callback();}
        }).fail(function(){
            log('custom pjax failed');
        });
    }

    function submit_the_form($form_link){
        var selected_bookmaker_name = $form_link.html();
        log("Submitting the form for " + selected_bookmaker_name + "..." );
        var bookmakers_list_form = $(form_id);
        $(field_id).val(selected_bookmaker_name);
        // log('bookmakers_list_form', bookmakers_list_form);
        bookmakers_list_form.submit();
    }

    function update_bookmaker_name_in_session(callback){
        // updates the bookmaker in bet slip if the page contains the bookmaker list. If the bookmaker is updates it
        // call the get bet slip to update the bet slip also. This action can't be done from the router after the update_bookmaker_name_in_session()
        // ends since it is async so we can't rely on its return value in the router code.
        log("updating session bookmaker...");
        var bookmakers_list_form = $(form_id);
        if (bookmakers_list_form[0] !== undefined) {
            var selected_bookmaker_name = bookmakers_list_form.find("#bookmaker_name").html().trim();
            log("bookmaker in list: " + selected_bookmaker_name);
            var selected_bookmaker_name_input = $(field_id);
            //log("(on ajax) selected_bookmaker_name_input: ", selected_bookmaker_name_input);
            selected_bookmaker_name_input.val(selected_bookmaker_name);
            log("bookmaker name to be sent: " + selected_bookmaker_name_input.val());

            $.ajax({
                url: window.location.pathname+'AjaxUpdSessionBookmaker/',
                type: 'POST',
                datatype: 'html',
                data: {
                    selected_bookmaker_name: selected_bookmaker_name,
                    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
                },
                success: function (data, status, xhr) {
                    log("bookmaker name in session was updated with: ", data);
                    //log("calling get bet slip (from update bookmaker name in session");
                    callback();
                },
                error: function(data) {
                    var message = "bookmaker name in session was NOT updated";
                    log(data, message);
                }
            });
        }else{
            log("There is no bookmakers list form in this page. No need to update the bookmaker in session");
        }
    }

    return {
        init: init,
        bind_events: bind_events,
        bind_pjax_events: bind_pjax_events,
        update_bookmaker_name_in_session: update_bookmaker_name_in_session
    }
});




