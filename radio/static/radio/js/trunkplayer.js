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

function set_scanner_ui(on) {
    $(".scanner-switch").attr("aria-checked", on ? "true" : "false");
}

function start_scanner() {
    active_play = 1;
    play_clip(silent_clip_url, 0);
    set_scanner_ui(true);
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
    $(".call.is-playing").removeClass("is-playing");
    set_play_icons();
    set_scanner_ui(false);
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
        pagination_html = '<button type="button" class="btn page-link" data-url="' + escape_html(window.location.pathname) + '">Latest</button> ';
        pagination_html += '<button type="button" class="btn page-link" data-url="' + escape_html(new_url) + '">Newer</button> ';
    }
    if(pagination_older_url) {
        pg_array = pagination_older_url.split( '?' );
        new_url = window.location.pathname + '?' + pg_array[1];
        pagination_html += '<button type="button" class="btn page-link" data-url="' + escape_html(new_url) + '">Older</button>';
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
    sync_scan_toggles();
    buildpage();
}

function clearpage() {
    $('#main-data-table').html('<div class="loading">Loading calls…</div>');
}

var scan_list_names = null;

function heading_html(kind, name, extra_html) {
    return '<div class="label">' + escape_html(kind) + '</div><h1 class="page-title">' + escape_html(name) + '</h1>' +
        (extra_html ? '<p>' + extra_html + '</p>' : '');
}

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
        var slugs = slug.toLowerCase().split('+');
        var list_names = $.map(slugs, function(s) {
            return s == 'default' ? 'All Talkgroups' : (scan_list_names && scan_list_names[s]) || s;
        });
        html = heading_html(slugs.length > 1 ? 'Scan lists' : 'Scan list', list_names.join(' + '),
            '<a href="/scan/' + escape_html(slug) + '/details/">Talkgroups in ' + (slugs.length > 1 ? 'these lists' : 'this list') + '</a>');
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
            names.push(label);
        }
        html = heading_html(names.length > 1 ? 'Talkgroups' : 'Talkgroup', names.join(', '), '');
    } else if (page_type == 'unit') {
        html = heading_html('Unit', slug.split('+').join(', '), '');
    }
    heading.html(html);
}

function load_scan_list_names() {
    $.getJSON('/api_v1/scanlist/', function(data) {
        scan_list_names = {};
        for (var a in data.results) {
            scan_list_names[data.results[a].slug] = data.results[a].name;
        }
        update_heading();
    });
}

function icon(name, size) {
    size = size || 16;
    return '<svg width="' + size + '" height="' + size + '" aria-hidden="true"><use href="#' + name + '"/></svg>';
}

// A scan list in the menu, its checkbox adds or removes it from what is playing
function scan_rail_item(slug, name, description) {
    return '<li class="menu-dynamic scan-rail-item"><a href="/scan/' + escape_html(slug) + '/" class="nav-item live-link" title="' + escape_html(description || '') + '">' +
        icon('i-list') + '<span>' + escape_html(name) + '</span></a>' +
        '<input type="checkbox" class="scan-toggle" value="' + escape_html(slug) + '" aria-label="Scan ' + escape_html(name) + ' with the other checked lists"></li>';
}

// Scan lists in the current /scan/a+b/ url
function active_scan_slugs() {
    var path = window.location.pathname.split('/');
    if ((path[1] != 'scan' && path[1] != 'scan2') || !path[2] || path[2] == 'default') {
        return [];
    }
    return decodeURIComponent(path[2]).toLowerCase().split('+');
}

function sync_scan_toggles() {
    var on = active_scan_slugs();
    $('.scan-toggle').each(function() {
        this.checked = on.indexOf(this.value) >= 0;
    });
}

function scan_toggle_url() {
    var slugs = $('.scan-toggle:checked').map(function() { return this.value; }).get();
    return '/scan/' + (slugs.length ? slugs.join('+') : 'default') + '/';
}

// Recorder system switch in the menu, see radio.views.recorder_system
function show_recorder_switch(data) {
    var section = $('#recorder-switch');
    var html = '';
    for (var i = 0; i < data.systems.length; i++) {
        var sys = data.systems[i];
        var on = sys.name == data.active;
        html += '<li><label class="nav-item recorder-option"' + (on ? ' aria-current="true"' : '') + '>' +
            '<input type="radio" name="recorder-system" value="' + escape_html(sys.name) + '"' + (on ? ' checked' : '') +
            (data.can_switch ? '' : ' disabled') + '>' + escape_html(sys.label) +
            (on && !data.running ? ' <span class="muted">(stopped)</span>' : '') + '</label></li>';
    }
    section.find('.rail-list').html(html);
    section.prop('hidden', !data.systems.length);
}

function load_recorder_switch() {
    $.getJSON('/api_v1/recorder/', show_recorder_switch);
}

function csrf_token() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
}

function rail_item(href, text, icon_name) {
    return '<li class="menu-dynamic"><a href="' + escape_html(href) + '" class="nav-item live-link">' + icon(icon_name) + escape_html(text) + '</a></li>';
}

// Highlight the menu entry for the page being shown
function mark_current_nav() {
    var here = window.location.pathname;
    $('.rail .nav-item').each(function() {
        if ($(this).attr('href') == here) {
            $(this).attr('aria-current', 'page');
        } else {
            $(this).removeAttr('aria-current');
        }
    });
}

function update_menu() {
    // Add the scan lists and talkgroups picked in the admin to the top of
    // the menus, the rest of each menu comes from site_live_nav.html
    $.getJSON('/api_v1/menuscanlist/', function(data) {
        var new_html = '';
        var section = '';
        for (var a in data.results) {
            // Scan lists are in menu order, a heading starts each new section
            if (data.results[a].section && data.results[a].section != section) {
                section = data.results[a].section;
                new_html += '<li class="menu-dynamic rail-sub label">' + escape_html(section) + '</li>';
            }
            new_html += scan_rail_item(data.results[a].scan_slug, data.results[a].scan_name, data.results[a].scan_description);
        }
        new_html = rail_item('/scan/default/', 'All Talkgroups', 'i-list') + new_html;
        $('#menu-scanlist .menu-dynamic').remove();
        $('#menu-scanlist').prepend(new_html);
        sync_scan_toggles();
        mark_current_nav();
    });

    $.getJSON('/api_v1/menutalkgrouplist/', function(data) {
        var new_html = '';
        for (var a in data.results) {
            new_html += rail_item('/tg/' + data.results[a].tg_slug + '/', data.results[a].tg_name, 'i-hash');
        }
        $('#menu-talkgrouplist .menu-dynamic').remove();
        $('#menu-talkgrouplist').prepend(new_html);
        mark_current_nav();
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
                    $("#main-message" ).prop('hidden', false);
                }
            }
        } else {
           last_message = "";
           $( "#main-message" ).prop('hidden', true);
        }
    })
    .fail(function() {
        last_message = "";
        $( "#main-message" ).prop('hidden', true);
    });
}

function audio_file_url(result) {
    var file_ext = result.audio_file_type || "mp3";
    return result.audio_url + result.audio_file + "." + file_ext;
}

// Colour stripe for a talkgroup, from the service type set in the admin
function service_class(service) {
    if (!service) {
        return '';
    }
    if (/fire/i.test(service)) {
        return ' svc-fire';
    }
    if (/police|law|sheriff|pd\b|patrol/i.test(service)) {
        return ' svc-law';
    }
    if (/ems|medic|ambulance|medical|hospital/i.test(service)) {
        return ' svc-ems';
    }
    return ' svc-other';
}

// What the now playing display shows for each call on the page
var call_info = {};
// Newest call shown before the last rebuild, to highlight new arrivals
var newest_seen = 0;

function build_row(curr_results) {
    var curr_id = curr_results.pk;
    var tg = curr_results.talkgroup_info;
    var tg_slug = escape_html(tg.slug);
    var is_muted = muted_tg[tg.slug];
    var classes = 'call' + service_class(tg.service);
    if (curr_results.emergency) { classes += ' is-emergency'; }
    if (is_muted) { classes += ' is-muted'; }
    if (curr_id == currently_playing) { classes += ' is-playing'; }
    if (newest_seen && curr_id > newest_seen) { classes += ' is-new'; }

    // Show units newest first, copy the list so we do not change the data
    var units = curr_results.units.slice().reverse();
    var unit_html = [];
    var unit_names = [];
    for (var u = 0; u < units.length; u++) {
        var unit = units[u];
        if(unit.description) {
            unit_html.push('<span class="unit">' + escape_html(unit.description) + '</span>');
            unit_names.push(unit.description);
        } else if(js_config.radio_change_unit) {
            unit_html.push('<a class="unit unknown unit-edit" href="/unitupdate/' + unit.pk + '/" title="Unknown radio, give it a name">?' + escape_html(unit.dec_id) + '</a>');
            unit_names.push('?' + unit.dec_id);
        } else {
            unit_html.push('<span class="unit unknown" title="Unknown radio">?' + escape_html(unit.dec_id) + '</span>');
            unit_names.push('?' + unit.dec_id);
        }
    }
    call_info[curr_id] = {
        tag: tg.alpha_tag,
        dec: 'TG ' + tg.dec_id,
        desc: [tg.description, unit_names.join(', ')].filter(Boolean).join(' · '),
        freq: curr_results.freq_mhz ? curr_results.freq_mhz + ' MHz' : ''
    };

    var html = '<div id="row-' + curr_id + '" class="' + classes + '">';
    if(curr_results.audio_file) {
        var playing_now = curr_id == currently_playing && !deck_paused;
        html += '<button type="button" aria-label="' + (playing_now ? 'Pause ' : 'Play ') + escape_html(tg.alpha_tag) + '" id="gl-player-action-' + curr_id + '" data-id="' + curr_id + '" data-audio-url="' + escape_html(audio_file_url(curr_results)) + '" class="play player-action">' + icon(playing_now ? 'i-pause' : 'i-play', is_muted ? 12 : 16) + '</button>';
    } else {
        html += '<button type="button" aria-label="No audio" class="play old-transmission" disabled>' + icon('i-ban', 16) + '</button>';
    }
    html += '<div class="tg"><div class="tg-line">';
    html += '<a class="tg-tag live-link" href="/tg/' + tg_slug + '/" title="Hold on this talkgroup">' + escape_html(tg.alpha_tag) + '</a>';
    if (curr_results.emergency) {
        html += '<span class="pill pill-emergency">Emergency</span>';
    }
    if (is_muted) {
        html += '<span class="pill pill-quiet">Muted</span>';
    }
    html += '</div><span class="tg-desc">' + escape_html(tg.description) + '</span></div>';
    html += '<div class="units">' + unit_html.join('') + '</div>';
    var len_pct = Math.max(4, Math.min(100, (curr_results.play_length || 0) / 60 * 100));
    html += '<div class="call-len" title="' + escape_html(curr_results.print_play_length) + '"><span style="width:' + len_pct.toFixed(0) + '%"></span></div>';
    html += '<div class="time"><span>' + escape_html(short_time(curr_results.local_start_datetime)) + '</span><small>' + escape_html(curr_results.print_play_length) + '</small></div>';

    html += '<div class="tran-menu">';
    if(curr_results.audio_file) {
        html += '<button type="button" class="more" aria-label="Call options" aria-haspopup="true" aria-expanded="false">' + icon('i-dots') + '</button>';
        html += '<div class="menu" role="menu" hidden>';
        html += '<a role="menuitem" href="/tg/' + tg_slug + '/" class="live-link">' + icon('i-hold') + 'Hold on talkgroup</a>';
        if (is_muted) {
            html += '<a role="menuitem" href="#" class="mute-link" data-tg="' + tg_slug + '">' + icon('i-vol') + 'Unmute talkgroup</a>';
        } else {
            html += '<a role="menuitem" href="#" class="mute-link" data-tg="' + tg_slug + '">' + icon('i-mute') + 'Mute talkgroup</a>';
        }
        if(js_config.download_audio) {
            html += '<a role="menuitem" href="/audio_download/' + escape_html(curr_results.slug) + '/">' + icon('i-dl') + 'Download audio</a>';
        }
        html += '<a role="menuitem" href="/audio/' + escape_html(curr_results.slug) + '/">' + icon('i-info') + 'Call details</a>';
        html += '</div>';
    }
    html += '</div>';
    html += '</div>';
    return html;
}

// The time of day part of the call start, the list is already in date order
function short_time(local_start) {
    var match = /(\d{1,2}:\d{2}(:\d{2})?)/.exec(local_start || '');
    return match ? match[1] : (local_start || '');
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
      $("#no_trans").prop('hidden', true);
      update_heading(data);
      last_update_time = Date.now();
      update_live_status();
      if(data.count > 0 && data.results.length > 0) {
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
              call_info = {};
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
              var pagination_html = update_pagination_links();
              if (pagination_html) {
                  new_html += '<div class="pager">' + pagination_html + '</div>';
              }
              $('#main-data-table').html(new_html);
              newest_seen = data.results[0].pk;
          }
          if (live_update == 1) {
              last_call = data.results[0].pk;
              first_load = 0;
          }
      } else {
        $("#no_trans").prop('hidden', false);
        $('#main-data-table').html("");
        curr_id_list = [];
        first_load = 0;
      }
    }).fail(function(jqXHR, textStatus) {
        if (textStatus != 'abort') {
            $('#main-data-table').html("");
            $("#no_trans").prop('hidden', false);
        }
    }).always(function() {
        buildpage_running = 0;
        if (buildpage_pending) {
            buildpage();
        }
    });
}

function click_play_clip(audio_file, audio_id){
    if (audio_id == currently_playing && audio_id != 0) {
        // Clicking the playing call pauses it, clicking again carries on
        toggle_pause();
        return true;
    }
    reset_play_list(audio_id);
    play_clip(audio_file, audio_id);
    return true;
}

function play_clip(audio_file, audio_id){
      currently_playing=audio_id;
      deck_paused = false;
      if(audio_id != 0) {
        $(".call.is-playing").removeClass("is-playing");
        $("#row-" + audio_id).addClass('is-playing');
        show_on_deck(call_info[audio_id] || button_info(audio_id));
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
      set_play_icons();
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
    $('.call.is-playing').removeClass('is-playing');
    currently_playing=0;
    deck_paused = false;
    set_play_icons();
    set_progress(0);
    $(document).prop('title', page_title);
}

// ---------- now playing deck ----------

var deck_paused = false;

// Details for a play button outside the call list (the call details page)
function button_info(audio_id) {
    var button = $('.player-action[data-id="' + audio_id + '"]');
    if (!button.length || !button.data('tag')) {
        return null;
    }
    return { tag: button.data('tag'), dec: button.data('dec'), desc: button.data('desc'), freq: button.data('freq') };
}

function show_on_deck(info) {
    if (!info) {
        return;
    }
    $('#lcd-tag').text(info.tag || '');
    $('#lcd-dec').text(info.dec || '');
    $('#lcd-desc').text(info.desc || '');
    $('#lcd-freq').text(info.freq || '');
}

function set_play_icons() {
    var playing = currently_playing != 0 && !deck_paused;
    $('#deck-play').attr('aria-label', playing ? 'Pause' : 'Play').find('use').attr('href', playing ? '#i-pause' : '#i-play');
    $('.call .player-action').each(function() {
        var is_this = $(this).data('id') == currently_playing && playing;
        $(this).find('use').attr('href', is_this ? '#i-pause' : '#i-play');
    });
}

function set_progress(percent) {
    $('#deck-progress-fill').css('width', percent + '%');
    $('#deck-progress').attr('aria-valuenow', Math.round(percent));
}

function toggle_pause() {
    if (currently_playing == 0) {
        // Nothing loaded, play the newest call on the page
        var first = $('.player-action').first();
        if (first.length) {
            click_play_clip(first.data('audio-url'), first.data('id'));
        }
        return;
    }
    if (deck_paused) {
        deck_paused = false;
        $("#jquery_jplayer_1").jPlayer("play");
    } else {
        deck_paused = true;
        $("#jquery_jplayer_1").jPlayer("pause");
    }
    set_play_icons();
}

function seek_to(percent) {
    if (currently_playing == 0) {
        return;
    }
    percent = Math.max(0, Math.min(100, percent));
    $("#jquery_jplayer_1").jPlayer("playHead", percent);
    set_progress(percent);
}

function setup_deck() {
    if (!is_player_page() && !$('.player-action').length) {
        return;
    }
    $('#deck').prop('hidden', false);
    $('body').addClass('has-deck');
    $('#deck-play').on('click', toggle_pause);
    $('.scanner-switch').on('click', function() {
        if (active_play) {
            stop_scanner();
        } else {
            start_scanner();
        }
    });
    $('#deck-progress').on('click', function(e) {
        seek_to((e.pageX - $(this).offset().left) / $(this).outerWidth() * 100);
    }).on('keydown', function(e) {
        var now = parseFloat($(this).attr('aria-valuenow')) || 0;
        if (e.key == 'ArrowRight') { e.preventDefault(); seek_to(now + 10); }
        if (e.key == 'ArrowLeft') { e.preventDefault(); seek_to(now - 10); }
    });
}

// ---------- live status in the top bar ----------

var last_update_time = 0;
var socket_open = false;

function update_live_status() {
    var status = $('#live-status');
    if (!status.length || !is_player_page()) {
        return;
    }
    status.prop('hidden', false);
    var text;
    if (!socket_open) {
        text = 'Connecting';
    } else {
        var secs = Math.round((Date.now() - last_update_time) / 1000);
        text = 'Live · ' + (!last_update_time || secs < 5 ? 'updated now' : secs < 90 ? 'updated ' + secs + 's ago' : 'updated ' + Math.round(secs / 60) + 'm ago');
    }
    status.toggleClass('is-live', socket_open);
    status.find('.live-text').text(text);
    status.attr('title', socket_open ? 'New calls appear as they come in' : 'Connecting for live updates');
}

// ---------- call menus, unit naming, theme and the mobile menu ----------

var open_menu = null;

function close_call_menu(rebuild) {
    if (!open_menu) {
        return;
    }
    open_menu.prop('hidden', true);
    open_menu.siblings('.more').attr('aria-expanded', 'false');
    open_menu = null;
    live_update = 1;
    if (rebuild !== false) {
        buildpage();
    }
}

function setup_page_controls() {
    // Dont rebuild the list while a call menu is open, it would close it
    $(document).on('click', '.call .more', function(e) {
        e.stopPropagation();
        var menu = $(this).siblings('.menu');
        if (open_menu && open_menu.is(menu)) {
            close_call_menu();
            return;
        }
        close_call_menu(false);
        live_update = 0;
        open_menu = menu;
        menu.prop('hidden', false);
        $(this).attr('aria-expanded', 'true');
        menu.find('a').first().focus();
    });
    $(document).on('click', function(e) {
        if (open_menu && !$(e.target).closest('.tran-menu').length) {
            close_call_menu();
        }
    });
    $(document).on('keydown', function(e) {
        if (e.key == 'Escape') {
            if (open_menu) {
                var button = open_menu.siblings('.more');
                close_call_menu(false);
                button.focus();
                live_update = 1;
            }
            close_rail();
        }
    });

    // Name an unknown radio
    $(document).on('click', 'a.unit-edit', function(e) {
        e.preventDefault();
        var dialog = document.getElementById('unitupdatemodal');
        $(dialog).find('.modal-content').load($(this).attr('href'), function() {
            if (dialog.showModal) {
                dialog.showModal();
            }
        });
    });
    $(document).on('click', '#unitupdatemodal [data-dismiss="modal"]', function() {
        document.getElementById('unitupdatemodal').close();
    });

    // Light / dark switch, remembered in this browser
    $('.theme-toggle').on('click', function() {
        var root = document.documentElement;
        var current = root.getAttribute('data-theme');
        if (!current) {
            current = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        }
        var next = current == 'dark' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('tp-theme', next); } catch (err) {}
    });

    // Slide out menu on small screens
    $('.rail-toggle').on('click', function() {
        if ($('#rail').hasClass('is-open')) {
            close_rail();
        } else {
            $('#rail').addClass('is-open');
            $('.rail-scrim').prop('hidden', false);
            $(this).attr('aria-expanded', 'true');
        }
    });
    $('.rail-scrim').on('click', close_rail);
    $(document).on('click', '#rail a', close_rail);
}

function close_rail() {
    $('#rail').removeClass('is-open');
    $('.rail-scrim').prop('hidden', true);
    $('.rail-toggle').attr('aria-expanded', 'false');
}

function setup_player() {
      $("#jquery_jplayer_1").jPlayer({
       ready: function () {
       },
       ended: function() {
           // Playing any clip (or the start button) turns on the scanner
           active_play=1;
           clip_finished();
           set_scanner_ui(true);
       },
       timeupdate: function(event) {
           if (currently_playing != 0) {
               set_progress(event.jPlayer.status.currentPercentAbsolute || 0);
           }
       },
       solution: "html",
       supplied: "mp3, m4a",
       remainingDuration: true,
       errorAlerts: false,
       warningAlerts: false,
       volume: 1,
       cssSelectorAncestor: "",
       cssSelector: {
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
           document.getElementById('unitupdatemodal').close();
      }
    });
  });
}


$(document).ready(function(){
    setup_player();
    setup_deck();
    setup_page_controls();
    mark_current_nav();
    if ($('#page-heading').length) {
        update_heading();
        load_scan_list_names();
    }
    updatemessage();
    setInterval(updatemessage, 30000);
    update_menu();

    if (is_player_page()) {
        first_load = 1;
        buildpage();
        start_socket();
        update_live_status();
        setInterval(play_next, 500);
        setInterval(update_live_status, 5000);
    }

    $(document).on('click', '.player-action', function(e) {
        e.preventDefault();
        click_play_clip($(this).data('audio-url'), $(this).data('id'));
    });
    $(document).on('click', '.mute-link', function(e) {
        e.preventDefault();
        close_call_menu(false);
        mute_click($(this).data('tg'));
    });
    $(document).on('click', '.page-link', function(e) {
        e.preventDefault();
        url_change($(this).data('url'));
    });
    load_recorder_switch();
    $(document).on('change', 'input[name="recorder-system"]', function() {
        var inputs = $('input[name="recorder-system"]').prop('disabled', true);
        $(this).closest('label').append(' <span class="muted switching">switching…</span>');
        $.ajax({
            url: '/api_v1/recorder/', type: 'POST', data: {system: this.value},
            headers: {'X-CSRFToken': csrf_token()},
            success: show_recorder_switch,
            error: function(xhr) {
                alert((xhr.responseJSON && xhr.responseJSON.error) || 'Could not switch the recorder');
                load_recorder_switch();
            }
        });
    });
    // Checking scan lists in the menu plays them all together
    $(document).on('change', '.scan-toggle', function() {
        var new_url = scan_toggle_url();
        if (is_player_page()) {
            live_update = 1;
            url_change(new_url);
            mark_current_nav();
        } else {
            window.location.href = new_url;
        }
    });
    // Stay on the page (and keep playing) when changing talkgroup/scan list
    $(document).on('click', 'a.live-link', function(e) {
        if (is_player_page() && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            e.preventDefault();
            close_call_menu(false);
            live_update = 1;
            url_change($(this).attr('href'));
            mark_current_nav();
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
        chatsock.onclose = null;
        chatsock.close();
        chatsock = null;
        socket_open = false;
    }
    var ws_url = socket_path();
    if (!ws_url || typeof ReconnectingWebSocket === 'undefined') {
        return false;
    }
    chatsock = new ReconnectingWebSocket(ws_scheme + '://' + window.location.host + ws_url);
    chatsock.onopen = function() {
        socket_open = true;
        update_live_status();
    };
    chatsock.onclose = function() {
        socket_open = false;
        update_live_status();
    };
    chatsock.onmessage = function(message) {
        // Dont move the list around while looking at older calls
        if (document.location.search.indexOf('page=') >= 0) {
            return;
        }
        buildpage();
    };
}
