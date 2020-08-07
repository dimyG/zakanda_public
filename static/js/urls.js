/**
 * Created by xene on 4/28/2016.
 */

define([], function () {

    var urls = {
        stats: {
            profile_template: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/Profile/',
            profile_template_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/Profile/'+'(\\d+)'),
            profile_data: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/Profile/'+'Data/',

            total_bet_detail: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/TotalBet/',
            total_bet_detail_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/TotalBet/'+'(\\d+)'),
            total_bet_list_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/TotalBetList/'+'(\\d+)'),
            bet_event_detail: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/BetEvent/',

            bet_events_table_template_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/BetEventsTable/'+'(\\d+)'),
            bet_events_table_data: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/BetEventsTable/Data/'
            //leader_board_template: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/LeaderBoard/',
            //leader_board_data: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Stats/LeaderBoard/Data/'


        },
        left_sidebar: {
            sports_list: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/LeftSidebar/SportsList/",
            user_info: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/LeftSidebar/UserInfo/",
            user_info_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/LeftSidebar/UserInfo/"),
            left_sidebar_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/LeftSidebar/")
        },
        user_accounts:{
            users_relation_list_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/Profile/(\\d+)/(\\w+)/"),
            stats_mode: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/StatsMode/",
            user_tips_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Users/Tips/"+"(\\d+)")
        },
        stream: {
            stream_user_data: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Feeds/StreamUserData/"
        },
        gutils: {
            misc_data: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Gutils/MiscData/",
            update_session: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Gutils/UpdateSession/",
            tips_overview_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Gutils/TipsOverview/")
        },
        games:{
            event: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Sports/Football/PlannedEvents/AllMarkets/",
            event_markets_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+'/Sports/Football/PlannedEvents/AllMarkets/'+'(\\d+)'),
            bets_picking_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/Sports/Football/")
        },
        bet_tagging:{
            deposit_create: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/BetGroup/Deposits/Create/",
            withdraw_create: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/BetGroup/Withdrawals/Create/",
            deposits_list_regex: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/BetGroup/Deposits/User/"+'(\\d+)'),
            bet_tag_list: new RegExp(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/BetGroup/List/User/"+'(\\d+)'),
            balance: location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '')+"/BetGroup/Balance/"
        }


    };

    urls['comment_urls'] = [
        // the urls that have a comments section
        urls.stats.total_bet_detail_regex,
        // urls.stats.profile_template_regex,
        urls.games.event_markets_regex
    ];

    return urls
});