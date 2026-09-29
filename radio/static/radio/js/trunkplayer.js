// Global Setup

// Live PlayBack, try and play next newest transmission. Stays off until the
// scanner is started (browsers block audio until the user clicks something)
active_play = 0;
// Live Update, pull new transmissions from site
live_update = 1;

currently_playing=0;
last_call = 0;
// Set base name from settings
var page_title = js_config.SITE_TITLE;
first_load = 1;
first_play = 1;
seen = [];
curr_id_list = [];
curr_file_list = [];
curr_tg_list = [];
curr_tg_slug_list = [];
var force_page_rebuild = 0;
var base_api_url = "/api_v1/";
var api_url = null;
var url_params = null;
var pagination_older_url = null;
var pagination_newer_url = null;
var muted_tg = {};

var base_audio_url = js_config.AUDIO_URL_BASE;
// Short silent clip used to unlock audio playback in the browser
var silent_clip_url = (js_config.STATIC_URL || '/static/') + 'radio/audio/point1sec.mp3';

// Is the page curently being built
var buildpage_running = 0;
// A rebuild was asked for while one was running
var buildpage_pending = 0;

// Escape text before putting it into the page
function escape_html(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function track_play(audio_id) {
    if (typeof gtag === 'function') {
        gtag('event', 'play', {'event_category': 'Transmission', 'event_label': String(audio_id)});
    }
}

// Is this a page that lists transmissions
function is_player_page() {
    return $('#main-data-table').length > 0;
}

function update_scan_list() {
    start_socket();
    force_page_rebuild = 1;
    first_load = 1;
    first_play = 1;
    buildpage();
}

function start_scanner() {
    active_play = 1;
    play_clip(silent_clip_url, 0);
    $(".stop-btn").show();
    $(".start-btn").hide();
}

function try_autostart() {
    // Test quietly with a plain audio element, the browser refuses
    // (and jPlayer would log an error) until the user clicks something
    var test = new Audio(silent_clip_url);
    test.volume = 0;
    var playing = test.play();
    if (playing && playing.then) {
        playing.then(function() {
            test.pause();
            start_scanner();
        }).catch(function() {});
    }
}

function stop_scanner() {
    $("#jquery_jplayer_1").jPlayer("stop");
    active_play = 0;
    currently_playing = 0;
    $(".active-trans").removeClass("active-trans");
    $(".stop-btn").hide();
    $(".start-btn").show();
    $(document).prop('title', page_title);
}

function mute_click(tg) {
    if (muted_tg[tg]) {
        muted_tg[tg] = false;
    } else {
        muted_tg[tg] = true;
    }
    live_update = 1; // Let page update to show the mute
    force_page_rebuild = 1;
    buildpage();
    return false;
}

function update_pagination_links() {
    var pagination_html = "";
    var pg_array, new_url;
    if(pagination_newer_url) {
        pg_array = pagination_newer_url.split( '?' );
        new_url = window.location.pathname + (pg_array[1] ? '?' + pg_array[1] : '');
        pagination_html = '<button class="btn btn-default page-link" data-url="' + escape_html(window.location.pathname) + '">Current</button> ';
        pagination_html += '<button class="btn btn-default page-link" data-url="' + escape_html(new_url) + '">Newer</button> ';
    }
    if(pagination_older_url) {
        pg_array = pagination_older_url.split( '?' );
        new_url = window.location.pathname + '?' + pg_array[1];
        pagination_html += '<button class="btn btn-default page-link" data-url="' + escape_html(new_url) + '">Older</button>';
    }
    return pagination_html;
}

function selected_talkgroups() {
    var select = $('.tg-multi-select');
    if (!select.length || !$.fn.select2) {
        return [];
    }
    return select.val() || [];
}

function update_api_url() {
    url_params = document.location.search;
    var pathArray = window.location.pathname.split( '/' );
    pathArray.shift();
    if(pathArray[0] == "scan2") {
      pathArray[0] = "scan";
    }
    if(pathArray[0] == "userscan") {
        // Build TGs from select box
        var tg_array = selected_talkgroups();
        if(tg_array.length) {
          api_url = base_api_url + "tg/" + tg_array.join('+') + "/";
        } else {
          api_url = null;
        }
    } else {
        api_url = base_api_url + pathArray.join('/');
    }
    if(api_url && url_params) {
        api_url = api_url + url_params;
    }
}

function url_change(new_url) {
    // Simple funcation to change url and rebuild the page
    window.history.pushState({}, page_title, new_url);
    load_current_url();
    return false;
}

function load_current_url() {
    clearpage();
    update_heading();
    $("#jquery_jplayer_1").jPlayer("stop");
    currently_playing = 0;
    last_call = 0;
    force_page_rebuild = 1;
    first_load = 1;
    first_play = 1;
    start_socket(); // Listen for calls on the new page
    buildpage();
}

function clearpage() {
    $('#main-data-table').html("<p style='text-align: center'><img src='" + (js_config.STATIC_URL || '/static/') + "radio/img/loader.gif' /></p>");
    $('#pagination').html("");
}

var scan_list_names = null;

// Show what this page is playing above the call list
function update_heading(data) {
    var heading = $('#page-heading');
    if (!heading.length) {
        return;
    }
    var pathArray = window.location.pathname.split('/');
    var page_type = pathArray[1];
    var slug = decodeURIComponent(pathArray[2] || '');
    var html = '';
    if (page_type == 'scan' || page_type == 'scan2') {
        var name = slug == 'default' ? 'All Talkgroups' : (scan_list_names && scan_list_names[slug.toLowerCase()]) || slug;
        html = '<strong>' + escape_html(name) + '</strong> &middot; <a href="/scan/' + escape_html(slug) + '/details/">Talkgroups in this list</a>';
    } else if (page_type == 'tg') {
        var names = [];
        var slugs = slug.toLowerCase().split('+');
        var results = (data && data.results) || [];
        for (var i = 0; i < slugs.length; i++) {
            var label = slugs[i];
            for (var r = 0; r < results.length; r++) {
                if (results[r].talkgroup_info.slug == slugs[i]) {
                    label = results[r].talkgroup_info.alpha_tag;
                    break;
                }
            }
            names.push(escape_html(label));
        }
        html = '<strong>Talkgroup' + (names.length > 1 ? 's ' : ' ') + names.join(', ') + '</strong>';
    } else if (page_type == 'unit') {
        html = '<strong>Unit ' + escape_html(slug.split('+').join(', ')) + '</strong>';
    }
    heading.html(html);
}

function load_scan_list_names() {
    $.getJSON('/api_v1/scanlist/', function(data) {
        scan_list_names = {};
        for (var a in data.results) {
            scan_list_names[data.results[a].slug] = data.results[a].description || data.results[a].name;
        }
        update_heading();
    });
}

function update_menu() {
    // Add the scan lists and talkgroups picked in the admin to the top of
    // the menus, the rest of each menu comes from site_live_nav.html
    $.getJSON('/api_v1/menuscanlist/', function(data) {
        var new_html = '';
        for (var a in data.results) {
            new_html += '<li class="menu-dynamic"><a href="/scan/' + escape_html(data.results[a].scan_slug) + '/" class="live-link">' + escape_html(data.results[a].scan_description) + '</a></li>';
        }
        if (!new_html) {
            new_html = '<li class="menu-dynamic"><a href="/scan/default/" class="live-link">All Talkgroups</a></li>';
        }
        $('#menu-scanlist .menu-dynamic').remove();
        $('#menu-scanlist').prepend(new_html);
    });

    $.getJSON('/api_v1/menutalkgrouplist/', function(data) {
        var new_html = '';
        for (var a in data.results) {
            new_html += '<li class="menu-dynamic"><a href="/tg/' + escape_html(data.results[a].tg_slug) + '/" class="live-link">' + escape_html(data.results[a].tg_name) + '</a></li>';
        }
        $('#menu-talkgrouplist .menu-dynamic').remove();
        $('#menu-talkgrouplist').prepend(new_html);
    });
}

var last_ajax;
var last_message;

function updatemessage() {
    $.getJSON("/api_v1/message/", function(data) {
        if(data.count > 0) {
            for (var a in data.results) {
                if(data.results[a]['mesg_type'] == 'A') {
                    // Message html is set by the site admin
                    var new_msge_data = data.results[a]['mesg_html'];
                    if(last_message != new_msge_data) {
                        $( "#main-message" ).html(new_msge_data);
                        last_message = new_msge_data;
                    }
                    $("#main-message" ).show();
                }
            }
        } else {
           last_message = "";
           $( "#main-message" ).hide();
        }
    })
    .fail(function() {
        last_message = "";
        $( "#main-message" ).hide();
    });
}

function audio_file_url(result) {
    var file_ext = result.audio_file_type || "mp3";
    return result.audio_url + result.audio_file + "." + file_ext;
}

function build_row(curr_results) {
    var curr_id = curr_results.pk;
    var tg = curr_results.talkgroup_info;
    var tg_muted = muted_tg[tg.slug] ? "mute-mute " : "";
    var new_html = '<div id="row-' + curr_id + '" class="row grad' + (curr_results.emergency ? ' emergency-trans' : '') + '">';
    new_html += '<div class="top-data">';
    if(curr_results.audio_file) {
        new_html += '<button aria-label="Play" id="gl-player-action-' + curr_id + '" data-id="' + curr_id + '" data-audio-url="' + escape_html(audio_file_url(curr_results)) + '" class="player-action glyphicon glyphicon-play"></button>';
    } else {
        new_html += '<button aria-label="No audio" class="old-transmission glyphicon glyphicon-ban-circle" disabled></button> ';
    }
    new_html += '<span class="talk-group ' + tg_muted + 'talk-group-' + escape_html(tg.slug) + '">' + escape_html(tg.alpha_tag) + '</span> ';
    new_html += '<span class="talk-group-descr">' + escape_html(tg.description) + ' </span>';
    if (curr_results.emergency) {
        new_html += '<span class="label label-danger emergency-label">EMERGENCY</span> ';
    }
    new_html += '<span class="tran-length">' + escape_html(curr_results.print_play_length) + '</span>';
    new_html += '<span class="tran-start-time">' + escape_html(curr_results.local_start_datetime) + '</span></div>';

    var unit_html = [];
    // Show units newest first, copy the list so we do not change the data
    var units = curr_results.units.slice().reverse();
    for (var u = 0; u < units.length; u++) {
        var unit = units[u];
        if(unit.description) {
            unit_html.push(escape_html(unit.description));
        } else if(js_config.radio_change_unit) {
            unit_html.push('?<a href="/unitupdate/' + unit.pk + '/" data-toggle="modal" data-target="#unitupdatemodal">' + escape_html(unit.dec_id) + '</a>');
        } else {
            unit_html.push('?' + escape_html(unit.dec_id));
        }
    }
    new_html += '<div class="unit-data"><span class="unit-id-1 unit-list">' + unit_html.join(', ') + '</span>';

    if(curr_results.audio_file) {
        var tg_slug = escape_html(tg.slug);
        new_html += '<span class="tran-menu">';
        new_html += '<div class="btn-group">';
        new_html += '<a class="btn dropdown-toggle tran-menu-a" data-toggle="dropdown" href="#">';
        new_html += '<i class="fa fa-list-ul" aria-hidden="false" title="Call Menu"></i>';
        new_html += '</a>';
        new_html += '<ul class="dropdown-menu pull-right">';
        new_html += '<li><a href="/tg/' + tg_slug + '/" class="live-link"><i class="fa fa-filter fa-fw" aria-hidden="true"></i> Hold on TalkGroup</a></li>';
        if (muted_tg[tg.slug]) {
            new_html += '<li><a href="#" class="mute-link" data-tg="' + tg_slug + '"><i class="fa fa-volume-up fa-fw"></i> Unmute TalkGroup</a></li>';
        } else {
            new_html += '<li><a href="#" class="mute-link" data-tg="' + tg_slug + '"><i class="fa fa-volume-off fa-fw"></i> Mute TalkGroup</a></li>';
        }
        if(js_config.download_audio) {
            new_html += '<li><a href="/audio_download/' + escape_html(curr_results.slug) + '/"><i class="fa fa-download fa-fw" aria-hidden="true"></i> Download audio file</a></li>';
        }
        new_html += '<li><a href="/audio/' + escape_html(curr_results.slug) + '/"><i class="fa fa-info-circle fa-fw" aria-hidden="true"></i> Details</a></li>';
        new_html += '</ul>';
        new_html += '</div>';
        new_html += '</span>';
    }
    new_html += '</div>';
    new_html += '</div>';
    return new_html;
}

function buildpage() {
    if(!is_player_page() || live_update == 0) {
       return false;
    }
    if(buildpage_running == 1) {
       // Run again once the current request finishes
       buildpage_pending = 1;
       return false;
    }
    update_api_url();
    if( ! api_url) {
        return false;
    }
    buildpage_running = 1;
    buildpage_pending = 0;
    last_ajax = $.getJSON(api_url, function(data) {
      $("#no_trans").hide();
      update_heading(data);
      if(data.count > 0 && data.results.length > 0) {
          $("#foot-play-button").show();
          if (live_update == 0) {
              // A call menu was opened while loading, try again once it closes
              force_page_rebuild = 1;
          } else if ( data.results[0].pk != last_call || force_page_rebuild == 1 ) {
              force_page_rebuild = 0;
              var new_html = '';
              var new_id_list = [];
              var new_file_list = [];
              var new_tg_list = [];
              var new_tg_slug_list = [];
              for (var a = 0; a < data.results.length; a++) {
                  var curr_results = data.results[a];
                  new_id_list.unshift(curr_results.pk);
                  new_file_list.unshift(audio_file_url(curr_results));
                  new_tg_list.unshift(curr_results.tg_name);
                  new_tg_slug_list.unshift(curr_results.talkgroup_info.slug);
                  new_html += build_row(curr_results);
              }
              curr_id_list = new_id_list;
              curr_file_list = new_file_list;
              curr_tg_list = new_tg_list;
              curr_tg_slug_list = new_tg_slug_list;
              pagination_older_url = data.next;
              pagination_newer_url = data.previous;
              new_html += '<div class="pagination-links">';
              new_html += update_pagination_links();
              new_html += '</div>';
              $('#main-data-table').html(new_html);
              if (currently_playing) {
                  $("#row-" + currently_playing).addClass('active-trans');
              }
          }
          if (live_update == 1) {
              last_call = data.results[0].pk;
              first_load = 0;
          }
      } else {
        $("#no_trans").show();
        $('#main-data-table').html("");
        curr_id_list = [];
        first_load = 0;
      }
    }).fail(function(jqXHR, textStatus) {
        if (textStatus != 'abort') {
            $('#main-data-table').html("");
            $("#no_trans").show();
        }
    }).always(function() {
        buildpage_running = 0;
        if (buildpage_pending) {
            buildpage();
        }
    });
}

function click_play_clip(audio_file, audio_id){
    reset_play_list(audio_id);
    play_clip(audio_file, audio_id);
    return true;
}

function play_clip(audio_file, audio_id){
      currently_playing=audio_id;
      if(audio_id != 0) {
        $(".active-trans").removeClass("active-trans");
        $("#row-" + audio_id).addClass('active-trans');
        track_play(audio_id);
      }
      if(audio_file.substring(audio_file.length - 3) == "m4a") {
        $("#jquery_jplayer_1").jPlayer("setMedia", {
           m4a: audio_file
        } );
      } else {
        $("#jquery_jplayer_1").jPlayer("setMedia", {
          mp3: audio_file
        } );
      }
      $("#jquery_jplayer_1").jPlayer("play");
}

function reset_play_list(audio_id){
    // Mark everything up to and including audio_id as heard
    seen.length = 0; // Clear the array
    for (var r_id = 0; r_id < curr_id_list.length; r_id++) {
        seen.push(curr_id_list[r_id]);
        if(curr_id_list[r_id] == audio_id) {
            break;
        }
    }
}

function play_next() {
    if(first_load == 1) {
        return false;
    }
    for (var r_id = 0; r_id < curr_id_list.length; r_id++) {
        if ( seen.indexOf( curr_id_list[r_id] ) < 0 ) {
            if ( currently_playing != 0) {
                break;
            }
            seen.push(curr_id_list[r_id]);
            // Dont play everything already on the page when it first loads,
            // or while the scanner is stopped
            if(first_play == 1 || active_play == 0) {
                continue;
            }
            // See if we are muted
            if(muted_tg[curr_tg_slug_list[r_id]]) {
               continue;
            }
            document.title = '>>' + curr_tg_list[r_id] + '<< ' + page_title;
            play_clip(curr_file_list[r_id], curr_id_list[r_id]);
            break;
        }
    }
    first_play = 0;
}

function clip_finished() {
    $('.active-trans').removeClass('active-trans');
    currently_playing=0;
    $(document).prop('title', page_title);
}

function setup_player() {
      $("#jquery_jplayer_1").jPlayer({
       ready: function () {
       },
       ended: function() {
           // Playing any clip (or the start button) turns on the scanner
           active_play=1;
           clip_finished();
           $(".stop-btn").show();
           $(".start-btn").hide();
       },
       solution: "html",
       supplied: "mp3, m4a",
       remainingDuration: true,
       errorAlerts: false,
       warningAlerts: false,
       volume: 1,
       cssSelectorAncestor: "",
       cssSelector: {
          title: "#title",
          play: "#jp1_play",
          pause: "#jp1_pause",
          stop: "#jp1_stop",
          mute: "#jp1_mute",
          unmute: "#jp1_unmute",
          currentTime: "#jp1_c_time",
         duration: "#jp1_duration"
       }
      });
      $("#jquery_jplayer_1").bind($.jPlayer.event.error + ".myProject", function(event) {
          console.log("Error Event: type = " + event.jPlayer.error.type + " " + event.jPlayer.error.context);
          // Skip the broken clip and move on to the next one
          clip_finished();
      });
  }

function unit_edit_post_setup1() {
    $("#unitupdatemodal").on("show.bs.modal", function(e) {
        var link = $(e.relatedTarget);
        $(this).find(".modal-content").load(link.attr("href"));
    });
}

function unit_edit_post_setup() {
    $('#update-unit-form').off('submit');
    $('#update-unit-form').trigger("reset");
    $('#update-unit-form').on('submit', function(e){
    e.preventDefault();
    $.ajax({
      url : $(this).attr('action'),
      type: "POST",
      data : $(this).serialize(),
      success: function(data){
           force_page_rebuild = 1;
           buildpage();
           $('#unitupdatemodal').modal('hide');
      }
    });
  });
}


$(document).ready(function(){
    $(".stop-btn").hide();
    setup_player();
    if ($('#page-heading').length) {
        update_heading();
        load_scan_list_names();
    }
    updatemessage();
    setInterval(updatemessage, 30000);
    update_menu();
    unit_edit_post_setup1();

    if (is_player_page()) {
        first_load = 1;
        buildpage();
        start_socket();
        setInterval(play_next, 500);
    }

    // Dont rebuild the list while a call menu is open, it would close it
    $(document).on('show.bs.dropdown', '.tran-menu .btn-group', function() {
        live_update = 0;
    });
    $(document).on('hidden.bs.dropdown', '.tran-menu .btn-group', function() {
        live_update = 1;
        buildpage();
    });
    $(document).on('click', '.player-action, .js-play', function(e) {
        e.preventDefault();
        click_play_clip($(this).data('audio-url'), $(this).data('id'));
    });
    $(document).on('click', '.mute-link', function(e) {
        e.preventDefault();
        mute_click($(this).data('tg'));
    });
    $(document).on('click', '.page-link', function(e) {
        e.preventDefault();
        url_change($(this).data('url'));
    });
    // Stay on the page (and keep playing) when changing talkgroup/scan list
    $(document).on('click', 'a.live-link', function(e) {
        if (is_player_page() && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            e.preventDefault();
            live_update = 1;
            url_change($(this).attr('href'));
        }
    });

    // Some browsers let us play without a click, if so the scanner starts
    try_autostart();
});

// Back/forward buttons after url_change()
window.addEventListener('popstate', function() {
    if (is_player_page()) {
        load_current_url();
    }
});

window.onfocus = function() {
    force_page_rebuild = 1;
    buildpage();
};

function play_from_start() {
    // Play entire page from start/bottom
    active_play = 1;
    first_load = 0;
    first_play = 0;
    seen = [];
    currently_playing = 0;
    play_next();
}

// Live updates, the server tells us when a new call arrives for this page

// When we're using HTTPS, use WSS too.
var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
var chatsock = null;

// Which websocket path to listen on for the current page, or null for none
function socket_path() {
    var pathArray = window.location.pathname.split( '/' );
    pathArray.shift();
    var page_type = pathArray[0];
    if (page_type == "scan2") {
        page_type = "scan";
    }
    if (page_type == "userscan") {
        var tg_array = selected_talkgroups();
        return tg_array.length ? "/ws-calls/tg/" + tg_array.join('+') + "/" : null;
    }
    if ((page_type == "scan" || page_type == "tg" || page_type == "unit") && pathArray[1]) {
        return "/ws-calls/" + page_type + "/" + pathArray[1] + "/";
    }
    return null;
}

function start_socket() {
    if(chatsock) {
        chatsock.close();
        chatsock = null;
    }
    var ws_url = socket_path();
    if (!ws_url || typeof ReconnectingWebSocket === 'undefined') {
        return false;
    }
    chatsock = new ReconnectingWebSocket(ws_scheme + '://' + window.location.host + ws_url);
    chatsock.onmessage = function(message) {
        // Dont move the list around while looking at older calls
        if (document.location.search.indexOf('page=') >= 0) {
            return;
        }
        buildpage();
    };
}
