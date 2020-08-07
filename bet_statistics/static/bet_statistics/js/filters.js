define([
    'd3',
    'crossfilter',
    'dc',
    './profile_stats',
    'js/utils'
], function(d3, crossfilter, dc, Profile_stats, Utils){

    var config = {
        bet_tags_select_id: '#bet_tags_filter'
    };

    var bet_tags_select_id = config.bet_tags_select_id;
    //var qs = null;
    var $select2_elem = null;

    function bet_tag_filtering(selected_tag_names, dim){
        //console.log('selected_tag_names: ', selected_tag_names);
        //console.log('bet tags dim: ', dim);
        if (dim){
            if (!selected_tag_names.length){
                // if the filter is clear
                dim.filterAll();
            }else {
                dim.filterFunction(function (d) {
                    if ($.inArray(d, selected_tag_names) != -1) {
                        return true
                    }
                });
            }
            dc.redrawAll();
        }
    }

    function get_selected_tag_values($this){
        var selected_tag_values = [];
        $this.parent().find(".select2-selection__choice").each(function(){
            selected_tag_values.push($(this).attr("title"))
        });
        return selected_tag_values;
    }

    function get_user_bet_tags(){
        var user_bet_tags = [];
        $(bet_tags_select_id).find("option").each(function(){
            user_bet_tags.push($(this).attr("value"));
        });
        return user_bet_tags
    }

    function add_url_params(selected_tag_names){
        //qs = (qs == null) ? new Utils.QS() : qs;
        var qs = new Utils.QS();
        for (var i=0; i<selected_tag_names.length; i++){
            qs.add(selected_tag_names[i], 'On');
        }
        //console.log("qs len:", Object.keys(qs.qs).length, qs.qs);
        // pjax doesn't work if you manually affect the state (with pushState or replaceState). As a workaround
        // we use the $.pjax.state
        history.replaceState($.pjax.state, null, "?" + qs.toString());
    }

    function remove_url_params(selected_tag_names){
        // the selected_tag_names contain the currently selected tags. Not the ones that have been removed.
        // So to remove them from qs object (and eventually from the url) we remove all bet tag keys from qs
        // and we add again the selected_tag_names as keys. This way the removed one is not present in qs.
        //qs = (qs == null) ? new Utils.QS() : qs;
        var user_bet_tags = get_user_bet_tags();
        var qs = new Utils.QS();
        qs.removeMany(user_bet_tags);
        for (var i=0; i<selected_tag_names.length; i++){
            qs.add(selected_tag_names[i], 'On');
        }
        //console.log("qs len:", Object.keys(qs.qs).length);
        var current_url = window.location.origin + window.location.pathname;
        Object.keys(qs.qs).length == 0 ?
            history.replaceState($.pjax.state, null, current_url) :
            history.replaceState($.pjax.state, null, "?" + qs.toString());
    }

    function get_url_parameters(url){
        var qs1 = new Utils.QS();
        var qs_params = qs1.qs;
        var selected_tag_names = [];
        var user_tags = get_user_bet_tags();
        // console.log('user tags: ', user_tags);
        for (var key in qs_params){
            if (qs_params.hasOwnProperty(key)){
                // console.log("extracted querystring param: ", key);
                if ($.inArray(key, user_tags) != -1){
                    // console.log('bet group in querystring: ', key);
                    // collect all querystring params that are tag names
                    selected_tag_names.push(key)
                }
            }
        }
        //console.log('selected_tag_names', selected_tag_names);
        return selected_tag_names
    }

    function programatically_select_tags(selected_tag_names){
        $select2_elem.val(selected_tag_names).trigger("change");
    }

    function apply_url_tag_filters(url){
        //console.log('applying url tag filters...');
        var selected_tag_names = get_url_parameters(url);
        var bet_tags_dim = Profile_stats.dimensions.bet_tags_dim;
        bet_tag_filtering(selected_tag_names, bet_tags_dim);
        programatically_select_tags(selected_tag_names);
    }


    function init(){
        $select2_elem = $(bet_tags_select_id).select2({
            placeholder: 'Select Bet Groups',
            allowClear: true
        });
    }

    function bind_events(){
        $(document).on('select2:select', bet_tags_select_id, function(){
            // log("select2:select triggered");
            var selected_tag_names = get_selected_tag_values($(this));
            var bet_tags_dim = Profile_stats.dimensions.bet_tags_dim;
            bet_tag_filtering(selected_tag_names, bet_tags_dim);
            add_url_params(selected_tag_names);
        });

        $(document).on('select2:unselect', bet_tags_select_id, function(){
            // log("select2:unselect triggered");
            var selected_tag_names = get_selected_tag_values($(this));
            var bet_tags_dim = Profile_stats.dimensions.bet_tags_dim;
            bet_tag_filtering(selected_tag_names, bet_tags_dim);
            remove_url_params(selected_tag_names);
        });

        $(document).on('profile_charts_rendered', function(){
            //console.log("profile_charts_rendered fired");
            var url = window.location.href;
            apply_url_tag_filters(url);
        })
    }

    return {
        bind_events: bind_events,
        init: init,
        bet_tag_filtering: bet_tag_filtering,
        apply_url_tag_filters: apply_url_tag_filters
    }
});
