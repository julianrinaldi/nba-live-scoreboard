"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,"../custom_components/nba_live_scoreboard/nba-live-game-card.js"),"utf8");

function harness(now = Date.now()) {
  const timers = new Map(), intervals = new Map(), fetches = [];
  const elements = new Map([["mlb-live-game-card",class {}],["nfl-live-game-card",class {}],["nhl-live-game-card",class {}]]);
  let serial = 0;
  const clock = { now };
  class TestElement {
    constructor() {
      this.isConnected = true; this.hidden = false; this.events = [];
      this.style = { setProperty(name,value) { this[name] = value; } };
    }
    toggleAttribute(name,value) { if (name === "hidden") this.hidden = value; }
    dispatchEvent(event) { this.events.push(event); return true; }
  }
  const context = {
    console:{info(){},debug(){}},HTMLElement:TestElement,Element:class {},URL,window:{},
    Date:class extends Date { static now() { return clock.now; } },
    CustomEvent:class { constructor(type,options) { this.type = type; Object.assign(this,options); } },
    customElements:{get:name=>elements.get(name),define:(name,value)=>elements.set(name,value)},
    setTimeout:(fn,delay)=>{const id=++serial;timers.set(id,{fn,delay});return id;},clearTimeout:id=>timers.delete(id),
    setInterval:(fn,delay)=>{const id=++serial;intervals.set(id,{fn,delay});return id;},clearInterval:id=>intervals.delete(id),
    requestAnimationFrame(){},fetch:url=>{fetches.push(url);return Promise.reject(new Error("Offline fixture"));},
  };
  vm.createContext(context);
  vm.runInContext(source+"\nglobalThis.api={Card:NbaLiveGameCard,CARD_DEFAULTS,CARD_CSS,EDITOR_SCHEMA,findNbaEntity,deepActiveElement,periodLabel,renderSituationRow,renderPossessionRow,renderCourt,renderScoringPlaysPanel,renderRecentPlays,teamStatsTablesHtml,playerCardBodyHtml,featuredPlayerLines,featuredStatTokens};",context);
  return {...context.api,context,timers,intervals,elements,fetches,clock};
}


function fixture() {
  return {
    league:"NBA",team_id:"18",team_abbr:"NY",team_name:"New York Knicks",
    display_event_id:"401809234",previous_event_id:"401809233",mode:"live",is_live:true,
    competition:{id:"401809234",date:"2099-10-22T23:00:00Z",season:2026,seasonType:2,
      status:{period:4,displayClock:"7:11",type:{state:"in",name:"STATUS_IN_PROGRESS"}},
      competitors:[
        {homeAway:"away",team:{id:"5",name:"Cavaliers",abbreviation:"CLE"},score:"100",recordSummary:"0-0",linescores:[{displayValue:"23"},{displayValue:"27"},{displayValue:"37"},{displayValue:"13"}]},
        {homeAway:"home",team:{id:"18",name:"Knicks",abbreviation:"NY"},score:"110",recordSummary:"0-0",linescores:[{displayValue:"33"},{displayValue:"32"},{displayValue:"22"},{displayValue:"23"}]},
      ]},
    away_team:{id:"5",name:"Cavaliers",abbreviation:"CLE"},home_team:{id:"18",name:"Knicks",abbreviation:"NY"},
    period_context:{period:4,display_clock:"7:11",display_period:"Q4",is_intermission:false,is_halftime:false},
    situation:{away_timeouts:2,home_timeouts:3,shot_clock:14,possession_team_id:"18"},
    featured_players:{
      away:{id:"3908809",display_name:"Donovan Mitchell",short_name:"D. Mitchell",game_stats:{points:"31",rebounds:"2",assists:"4",field_goals:"12-25"}},
      home:{id:"3934672",display_name:"Jalen Brunson",short_name:"J. Brunson",headshot:"https://example.test/brunson.png",game_stats:{points:"23",rebounds:"3",assists:"5",field_goals:"5-18"}},
    },
    current_period:{id:"4",number:4,label:"Q4",play_count:30,points:36,away_points:13,home_points:23,is_current:true},
    recent_plays:[{id:"basket1",text:"Jalen Brunson makes three point jumper",period:4,clock:"7:11",team_id:"18",scoring_play:true,score_value:3,away_score:100,home_score:110,is_shot:true,points_attempted:3,coordinate:{}}],
    leaders:{away:[{id:"3908809",name:"Donovan Mitchell",category:"Points",value:"31"}],home:[{id:"3934672",name:"Jalen Brunson",category:"Points",value:"23"}]},
    team_stats:{away:{team_id:"5",name:"Cavaliers",categories:[{name:"players",label:"Players",columns:["PTS","REB"],keys:["points","rebounds"],rows:[{id:"3908809",name:"Donovan Mitchell",position:"G",stats:["31","2"]}],totals:[]}]},home:{team_id:"18",name:"Knicks",categories:[]}},
  };
}
function cardFor(h,attrs=fixture(),config={}) {
  const card=new h.Card();card.content={innerHTML:"",contains:()=>true,querySelector:()=>null};card.card={};
  card._hass={states:{"sensor.nba_live_scoreboard_ny":{state:attrs.display_event_id,attributes:attrs}}};
  card.setConfig({entity:"sensor.nba_live_scoreboard_ny",...config});card.render();return card;
}
const tick=async()=>{await Promise.resolve();await Promise.resolve();await Promise.resolve();};

const WINDOW_NOW = Date.parse("2026-09-03T16:00:00Z");
function upcoming(hours = 25) {
  const attrs = fixture();
  attrs.is_live = attrs.game_active = false; attrs.mode = "next";
  attrs.competition.status = {period:0,type:{state:"pre",name:"STATUS_SCHEDULED",completed:false}};
  attrs.next_game_start = attrs.competition.date = new Date(WINDOW_NOW + hours * 3600000).toISOString();
  return attrs;
}
function fireVisibilityTimer(h,card,now) {
  const id=card._visibilityTimer, timer=h.timers.get(id);
  assert(timer); h.timers.delete(id); h.clock.now=now; timer.fn();
}
test("hours window defaults to disabled and is available in the visual editor",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h,upcoming(200));
  assert.equal(h.CARD_DEFAULTS.show_within_hours,0);assert.equal(card.hidden,false);
  assert.equal(card._visibilityTimer,null);
  const field=h.EDITOR_SCHEMA.flatMap(s=>s.schema||[s]).find(s=>s.name==="show_within_hours");
  assert.equal(field.selector.number.min,0);assert.equal(field.selector.number.step,0.5);
});
test("hours validation accepts fractional numeric hours and blank disables without changing other options",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h);
  for(const value of [undefined,null,"", " ",0,"0"]) {
    card.setConfig({entity:"sensor.nba_live_scoreboard_ny",show_within_hours:value,show_linescore:true});
    assert.equal(card.config.show_within_hours,0);assert.equal(card.config.show_linescore,true);
  }
  card.setConfig({show_within_hours:"1.5"});assert.equal(card.config.show_within_hours,1.5);
  for(const value of [-1,"-2",Infinity,NaN,"NaN","nonsense",true,false,[],{}])
    assert.throws(()=>card.setConfig({show_within_hours:value}),/non-negative number/);
});
test("24 hours hides only outside the inclusive boundary, with no visible layout space",()=>{
  const h=harness(WINDOW_NOW),attrs=upcoming(24+1/3600000),card=cardFor(h,attrs,{show_within_hours:24});
  assert.equal(card.hidden,true);assert.equal(card.style.display,"none");assert.equal(card.getCardSize(),0);
  assert.equal(card.connectedWhileHidden,true);assert.equal(h.timers.get(card._visibilityTimer).delay,1);
  fireVisibilityTimer(h,card,WINDOW_NOW+1);
  assert.equal(card.hidden,false);assert.equal(card.style.display,"");assert.equal(card.getCardSize(),4);
  assert.match(card.content.innerHTML,/compact-mode/);
  const event=card.events.at(-1);assert.equal(event.type,"card-visibility-changed");
  assert.equal(event.detail.value,true);assert.equal(event.bubbles,true);assert.equal(event.composed,true);
});
test("hidden cards wake with refresh rate zero without a new HA state",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h,upcoming(25),{show_within_hours:24,refresh_rate:0});
  assert.equal(h.intervals.size,0);assert.equal(h.timers.get(card._visibilityTimer).delay,60000);
  fireVisibilityTimer(h,card,WINDOW_NOW+3600000);
  assert.equal(card.hidden,false);assert.equal(h.intervals.size,0);
  const count=card.events.length;card.render();assert.equal(card.events.length,count);
});
test("window handles timezone offsets, fractional values and long waits without timer overflow",()=>{
  const h=harness(WINDOW_NOW),attrs=upcoming();attrs.next_game_start="2026-09-03T13:30:00-04:00";
  const card=cardFor(h,attrs,{show_within_hours:1.5});assert.equal(card.hidden,false);
  attrs.next_game_start="2099-10-22T23:00:00Z";card.render();assert.equal(card.hidden,true);
  assert.equal(h.timers.get(card._visibilityTimer).delay,60000);
});
test("live, halftime and in-progress delay bypass the window, but pregame delay does not",()=>{
  const h=harness(WINDOW_NOW),attrs=fixture();attrs.next_game_start=null;
  const card=cardFor(h,attrs,{show_within_hours:1});assert.equal(card.hidden,false);
  attrs.competition.status.type.name="STATUS_HALFTIME";card.render();assert.equal(card.hidden,false);
  attrs.is_delayed=true;attrs.competition.status.type.name="STATUS_DELAYED";card.render();assert.equal(card.hidden,false);
  attrs.competition.status.period=0;attrs.period_context.period=0;card.render();assert.equal(card.hidden,true);
});
test("final hides despite stale live flags, unless the actual next game is within the window",()=>{
  const h=harness(WINDOW_NOW),attrs=fixture();attrs.mode="final";
  attrs.competition.status.type={state:"post",completed:true,name:"STATUS_FINAL"};
  attrs.next_game_start=upcoming(25).next_game_start;
  const card=cardFor(h,attrs,{show_within_hours:24});assert.equal(card.hidden,true);
  attrs.next_game_start=upcoming(12).next_game_start;card.render();assert.equal(card.hidden,false);
  attrs.next_game_start=null;card.render();assert.equal(card.hidden,true);
});
test("cancelled, postponed and unavailable dates cannot count as an active game",()=>{
  const h=harness(WINDOW_NOW);
  for(const name of ["STATUS_CANCELED","STATUS_CANCELLED","STATUS_POSTPONED"]){
    const attrs=fixture();attrs.competition.status.type={name,state:"post",completed:false};
    attrs.next_game_start=null;assert.equal(cardFor(h,attrs,{show_within_hours:24}).hidden,true);
  }
  for(const value of [null,"","bad","2026-09-03T17:00:00",true]){
    const attrs=upcoming(1);attrs.next_game_start=value;
    assert.equal(cardFor(h,attrs,{show_within_hours:24}).hidden,true);
  }
});
test("scheduled game does not disappear at tipoff, and stale pregame expires after six hours",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h,upcoming(0),{show_within_hours:1});
  assert.equal(card.hidden,false);fireVisibilityTimer(h,card,WINDOW_NOW+30000);assert.equal(card.hidden,false);
  fireVisibilityTimer(h,card,WINDOW_NOW+6*3600000+1);assert.equal(card.hidden,true);
});
test("visibility ignores schedule navigation and resets navigation on hide",()=>{
  const h=harness(WINDOW_NOW),attrs=upcoming(12),card=cardFor(h,attrs,{show_within_hours:24});
  card._navOffset=1;card._navGameData=upcoming(100);card.render();assert.equal(card.hidden,false);
  attrs.next_game_start=upcoming(48).next_game_start;card.render();assert.equal(card.hidden,true);
  assert.equal(card._navOffset,0);assert.equal(card._navGameData,null);
});
test("preview and edit mode show the card, while idle hides and diagnostics stay readable",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h,upcoming(48),{show_within_hours:24});
  assert.equal(card.hidden,true);card.preview=true;assert.equal(card.hidden,false);
  card.preview=false;assert.equal(card.hidden,true);card.editMode=true;assert.equal(card.hidden,false);
  card.editMode=false;assert.equal(card.hidden,true);
  card._hass.states[card.config.entity].state="unavailable";card.render();assert.equal(card.hidden,false);
  card.setConfig({entity:"sensor.missing",show_within_hours:24});assert.equal(card.hidden,false);
  assert.match(card.content.innerHTML,/Entity not found/);
  card.setConfig({show_within_hours:24});assert.equal(card.hidden,false);
  assert.equal(cardFor(h,{mode:"idle",team_abbr:"NY",next_game_start:null},{show_within_hours:24}).hidden,true);
});
test("window disconnect clears timers, reconnect wakes, and disabling immediately restores visibility",()=>{
  const h=harness(WINDOW_NOW),card=cardFor(h,upcoming(25),{show_within_hours:24,refresh_rate:10});
  card.isConnected=false;card.disconnectedCallback();assert.equal(h.timers.size,0);assert.equal(h.intervals.size,0);
  h.clock.now+=3600000;card.isConnected=true;card.connectedCallback();assert.equal(card.hidden,false);
  assert.equal(h.timers.size,1);assert.equal(h.intervals.size,1);
  card.setConfig({entity:card.config.entity,show_within_hours:0});assert.equal(card.hidden,false);
  assert.equal(h.timers.size,0);assert.equal(h.intervals.size,0);
});
test("hiding closes dialogs and invalidates pending navigation without opening network requests",()=>{
  const h=harness(WINDOW_NOW),attrs=upcoming(12),card=cardFor(h,attrs,{show_within_hours:24});
  let closed=0;card._destroyPlayerCardPopup=()=>closed++;card._destroyLineupPopup=()=>closed++;
  const generation=card._navGeneration,fetchCount=h.fetches.length;
  attrs.next_game_start=upcoming(48).next_game_start;card.render();assert.equal(closed,2);
  assert(card._navGeneration>generation);assert.equal(h.fetches.length,fetchCount);
});
test("older integration fallback is limited to confirmed pregame dates, never explicit null or TBD",()=>{
  const h=harness(WINDOW_NOW),attrs=upcoming(12);delete attrs.next_game_start;
  assert.equal(cardFor(h,attrs,{show_within_hours:24}).hidden,false);
  for(const mutate of [a=>a.competition.timeValid=false,a=>a.competition.dateValid=false,
    a=>a.competition.isTBDFlex=true,a=>a.competition.status.type.detail="Time TBD",
    a=>a.next_game_start=null]) {
    const value=JSON.parse(JSON.stringify(attrs));mutate(value);
    assert.equal(cardFor(h,value,{show_within_hours:24}).hidden,true);
  }
});

test("NBA element, cache, options and CSS coexist with MLB, NFL and NHL",()=>{
  const h=harness();for(const name of ["mlb-live-game-card","nfl-live-game-card","nhl-live-game-card","nba-live-game-card","nba-live-game-card-editor"])assert(h.elements.has(name));
  assert.equal(h.CARD_DEFAULTS.live_default_view,"collapsed");assert.equal(h.CARD_DEFAULTS.show_shot_chart,false);assert.equal(h.CARD_DEFAULTS.show_period_nav,true);
  assert(!Object.keys(h.CARD_DEFAULTS).some(k=>/quarterback|drive|timeout|field|batter|pitch|inning|diamond|on_deck/.test(k)));
  const selectors=h.CARD_CSS.match(/[^{}]+(?=\{)/g);assert(selectors.every(g=>g.split(",").every(s=>s.trim().startsWith("nba-live-game-card "))));
});
test("renamed NFL and NHL sensors are never selected as NBA sensors",()=>{
  const h=harness();const states={"sensor.football":{attributes:{league:"NFL",team_abbr:"NYG",display_event_id:"1",period_context:{}}},"sensor.hockey":{attributes:{league:"NHL",team_abbr:"NYR",display_event_id:"2",period_context:{}}},"sensor.basketball":{attributes:{league:"NBA",team_abbr:"NY",display_event_id:"3",period_context:{}}}};
  assert.equal(h.findNbaEntity({states}),"sensor.basketball");delete states["sensor.basketball"];assert(!h.findNbaEntity({states}));
});
test("missing configuration, entity and off-season data have useful messages",()=>{
  const h=harness(),card=cardFor(h);card.setConfig({});card.render();assert.match(card.content.innerHTML,/choose an NBA Live Scoreboard entity/);
  card.setConfig({entity:"sensor.nope"});card.render();assert.match(card.content.innerHTML,/Entity not found/);
  assert.match(cardFor(h,{league:"NBA",team_abbr:"NY",display_event_id:"",mode:"idle"}).content.innerHTML,/No NBA game is currently available/);
});
test("live view starts collapsed and loads featured-player portraits only after expansion",()=>{
  const h=harness(),card=cardFor(h);assert.match(card.content.innerHTML,/aria-expanded="false"/);assert.doesNotMatch(card.content.innerHTML,/Brunson/);assert.equal(h.fetches.length,0);
  card._toggleLiveExpand();assert.match(card.content.innerHTML,/Brunson/);assert(h.fetches.length>0);
  assert.doesNotMatch(card.content.innerHTML,/Down:|To go:|Ball on:|YDS|Quarterback|Touchdown/);
  card._toggleLiveExpand();assert.doesNotMatch(card.content.innerHTML,/Brunson/);
});
test("clock, timeouts, possession and featured-player-stat updates repaint",()=>{
  const h=harness(),a=fixture(),card=cardFor(h,a,{live_default_view:"expanded"});
  for(const change of [()=>a.period_context.display_clock="7:10",()=>a.situation.away_timeouts=1,()=>a.situation.possession_team_id="5",()=>a.featured_players.away.game_stats.points="32"]){const before=card.content.innerHTML;change();card.render();assert.notEqual(card.content.innerHTML,before);}
  assert.match(card.content.innerHTML,/7:10/);
});
test("a new game resets live expansion",()=>{
  const h=harness(),a=fixture(),card=cardFor(h,a);card._toggleLiveExpand();a.display_event_id="401809235";a.competition.id=a.display_event_id;card.render();assert.match(card.content.innerHTML,/aria-expanded="false"/);
});
test("compact final and pregame remain expandable without inventing starters",()=>{
  const h=harness(),a=fixture();a.is_live=false;a.mode="final";a.competition.status.type={state:"post",completed:true,name:"STATUS_FINAL"};
  const card=cardFor(h,a);assert.match(card.content.innerHTML,/compact-mode/);card._upcomingExpanded=true;card._lastFingerprint="";card._lastCompactFp="";card.render();assert.match(card.content.innerHTML,/Game Leaders/);
  a.mode="next";a.competition.status.type={state:"pre",name:"STATUS_SCHEDULED"};a.featured_players={away:{},home:{}};card._lastFingerprint="";card.render();assert.doesNotMatch(card.content.innerHTML,/Brunson|Projected QB/);
});
test("postponed and delayed games do not masquerade as final zero-zero",()=>{
  const h=harness(),a=fixture();a.is_live=false;a.competition.status.type={state:"post",completed:false,name:"STATUS_POSTPONED"};const card=cardFor(h,a);assert.match(card.content.innerHTML,/PPD/);assert.doesNotMatch(card.content.innerHTML,/final-score/);
  a.is_delayed=true;a.competition.status.type={state:"in",name:"STATUS_DELAYED",detail:"Delayed"};card.render();assert.match(card.content.innerHTML,/Delayed/);
});
test("a full period retains every play in a keyboard-scrollable newest-first list without mutating input",()=>{
  const h=harness();const plays=Array.from({length:94},(_,i)=>({id:String(i),period:2,text:"Play number "+String(i).padStart(2,"0")}));
  const before=JSON.stringify(plays);const html=h.renderRecentPlays(plays,h.CARD_DEFAULTS);
  assert.equal((html.match(/class="play-row"/g)||[]).length,94);assert(html.indexOf("Play number93")<html.indexOf("Play number00") || html.indexOf("Play number 93")<html.indexOf("Play number 00"));
  assert.equal(JSON.stringify(plays),before);assert.match(html,/tabindex="0"/);assert.match(html,/role="region"/);assert.match(html,/aria-label=/);
  assert.match(h.CARD_CSS,/\.plays-panel[^}]*max-height:\s*320px/);assert.match(h.CARD_CSS,/\.plays-panel[^}]*overflow-y:\s*auto/);
});
test("live repaint preserves play-list reading position and keyboard focus within one period",()=>{
  const h=harness(),a=fixture(),card=cardFor(h,a,{live_default_view:"expanded"});
  const oldPanel=new h.context.HTMLElement(),newPanel=new h.context.HTMLElement();oldPanel.scrollTop=120;oldPanel.scrollHeight=500;newPanel.scrollHeight=550;newPanel.scrollTop=0;
  let focused=0;newPanel.focus=options=>{assert.equal(options.preventScroll,true);focused++;h.context.document.activeElement=newPanel;};
  h.context.document={activeElement:oldPanel};let panel=oldPanel,html=card.content.innerHTML;
  card.content.querySelector=selector=>selector===".plays-panel"?panel:null;
  Object.defineProperty(card.content,"innerHTML",{get:()=>html,set:value=>{html=value;panel=newPanel;}});
  a.period_context.display_clock="7:10";card.render();assert.equal(newPanel.scrollTop,170);assert.equal(focused,1);
  a.period_context.period=5;a.period_context.display_clock="4:59";card.render();assert.equal(newPanel.scrollTop,0);
});
test("schedule navigation uses NBA route and returns after 60 seconds",async()=>{
  const h=harness(),card=cardFor(h),calls=[],neighbor=fixture();neighbor.display_event_id="401809235";neighbor.is_live=false;neighbor.mode="next";neighbor.competition.status.type={state:"pre",name:"STATUS_SCHEDULED"};
  card._hass.connection={sendMessagePromise:async r=>{calls.push(r);return {offset:1,game_data:neighbor,has_prev:true,has_next:false};}};card._navigateSchedule(1);await tick();assert.equal(calls[0].type,"nba_live_scoreboard/game_at_offset");assert.equal(card._navOffset,1);
  const timer=[...h.timers.values()].find(t=>t.delay===60000);assert(timer);timer.fn();assert.equal(card._navOffset,0);
});
test("stale schedule responses cannot replace a new selection",async()=>{
  const h=harness(),card=cardFor(h);let resolve;card._hass.connection={sendMessagePromise:()=>new Promise(r=>{resolve=r;})};card._navigateSchedule(1);card._resetScheduleNav();resolve({offset:1,game_data:fixture()});await tick();assert.equal(card._navOffset,0);assert.equal(card._navGameData,null);
});
test("period pager rolls back clocks and scores and returns after 20 seconds",async()=>{
  const h=harness(),card=cardFor(h,fixture(),{live_default_view:"expanded"}),calls=[];
  card._hass.connection={sendMessagePromise:async r=>{calls.push(r);return {offset:-1,total_periods:4,is_current:false,has_prev:true,has_next:true,away_score:87,home_score:87,period_context:{period:3,display_clock:""},current_period:{id:"3",number:3,label:"Q3",play_count:30,points:59},recent_plays:[{id:"old",period:3,clock:"11:58",text:"Earlier two point basket",away_score:87,home_score:87}]};}};
  card._navigatePeriod(-1);await tick();assert.equal(calls[0].type,"nba_live_scoreboard/period_at_offset");assert.match(card.content.innerHTML,/Earlier period/);assert.match(card.content.innerHTML,/Earlier two point basket/);assert.doesNotMatch(card.content.innerHTML,/Game scoring leader/);
  const timer=[...h.timers.values()].find(t=>t.delay===20000);assert(timer);timer.fn();assert.equal(card._periodOffset,0);assert.match(card.content.innerHTML,/7:11/);
});
test("an earlier period with an explicit blank countdown never inherits the live clock",async()=>{
  const h=harness(),a=fixture();
  a.period_context.period=3;a.competition.status.period=3;a.current_period={id:"3",number:3,label:"Q3"};
  a.period_context.display_clock="5:00";a.competition.status.displayClock="5:00";
  const card=cardFor(h,a,{live_default_view:"expanded"});
  assert.match(card.content.innerHTML,/5:00/);
  card._hass.connection={sendMessagePromise:async()=>({
    offset:-1,total_periods:3,is_current:false,has_prev:true,has_next:true,
    away_score:0,home_score:0,
    period_context:{period:2,display_clock:"",display_period:"Q2"},
    current_period:{id:"2",number:2,label:"Q2",play_count:1,points:2},
    recent_plays:[{id:"earlier",period:2,clock:"11:58",text:"Earlier two point basket"}],
  })};
  card._navigatePeriod(-1);await tick();
  assert.equal(card._periodOffset,-1);
  assert.match(card.content.innerHTML,/Earlier period · Q2<\/div>/);
  assert.doesNotMatch(card.content.innerHTML,/5:00/);
  assert.match(card.content.innerHTML,/11:58/);
  card._navigatePeriod(1);
  assert.equal(card._periodOffset,0);
  assert.doesNotMatch(card.content.innerHTML,/Earlier period/);
  assert.match(card.content.innerHTML,/5:00/);
});
test("stale period responses are discarded after resets",async()=>{
  const h=harness(),card=cardFor(h);let resolve;card._hass.connection={sendMessagePromise:()=>new Promise(r=>{resolve=r;})};card._navigatePeriod(-1);card._resetPeriodNav();resolve({offset:-1,recent_plays:[],current_period:{id:"old"}});await tick();assert.equal(card._periodOffset,0);assert.equal(card._periodView,null);
});
test("configuration edits invalidate memoized compact markup",()=>{
  const h=harness(),a=fixture();a.is_live=false;a.mode="next";a.competition.status.type={state:"pre",name:"STATUS_SCHEDULED"};const card=cardFor(h,a);assert.match(card.content.innerHTML,/schedule-nav-btn/);card.setConfig({entity:"sensor.nba_live_scoreboard_ny",show_schedule_nav:false});card.render();assert.doesNotMatch(card.content.innerHTML,/schedule-nav-btn/);
});
test("profile and team-season requests deduplicate and cache",async()=>{
  const h=harness(),card=cardFor(h),calls=[];card._hass.connection={sendMessagePromise:async r=>{calls.push(r);return r.type.endsWith("player_card")?{player_card:{bio:{name:"Donovan Mitchell"}}}:{season_stats:{"3908809":{season:2026,categories:{}}}};}};
  await Promise.all([card._fetchPlayerCard("3908809"),card._fetchPlayerCard("3908809")]);await card._fetchPlayerCard("3908809");assert.equal(calls.length,1);
  await Promise.all([card._fetchTeamSeasonStats("away"),card._fetchTeamSeasonStats("away")]);await card._fetchTeamSeasonStats("away");assert.equal(calls.length,2);assert.equal(calls[1].type,"nba_live_scoreboard/team_season_stats");assert.deepEqual(Array.from(calls[1].athlete_ids),["3908809"]);
});
test("disconnect clears navigation and timers; reconnect rearms local refresh",()=>{
  const h=harness(),card=cardFor(h,fixture(),{refresh_rate:10});card._navOffset=2;card._navGameData=fixture();card._periodOffset=-1;card._periodView={recent_plays:[]};card._armNavIdleTimer();card._armPeriodIdleTimer();card._setupRefreshTimer();const nav=card._navGeneration,period=card._periodGeneration;
  card.disconnectedCallback();assert.equal(card._navOffset,0);assert.equal(card._periodOffset,0);assert.equal(h.timers.size,0);assert.equal(h.intervals.size,0);assert(card._navGeneration>nav);assert(card._periodGeneration>period);card.hass=card._hass;assert.equal(h.intervals.size,0);card.connectedCallback();assert.equal(h.intervals.size,1);
});
test("native highlight anchors retain normal click and keyboard activation",()=>{
  const h=harness(),card=cardFor(h),anchor=new h.context.Element();anchor.closest=s=>s.includes("a[href]")?anchor:null;let prevented=0;const event={target:anchor,key:"Enter",preventDefault(){prevented++;},stopPropagation(){}};card._onContentClick(event);card._onContentKeydown(event);event.key=" ";card._onContentKeydown(event);assert.equal(prevented,0);
});
test("keyboard player activation happens once, without doubling native buttons",()=>{
  const h=harness(),card=cardFor(h),link=new h.context.Element();link.closest=s=>s===".player-link"?link:null;let opened=0;card._openPlayerProfile=()=>{opened++;return true;};card._onContentKeydown({target:link,key:"Enter",preventDefault(){}});assert.equal(opened,1);const button=new h.context.Element();button.closest=s=>s.includes("button")?button:null;card._onContentKeydown({target:button,key:"Enter",preventDefault(){}});assert.equal(opened,1);
});
test("popup focus traverses HA shadow roots and restores replaced openers",()=>{
  const h=harness(),card=cardFor(h),leaf=new h.context.HTMLElement();h.context.document={activeElement:{shadowRoot:{activeElement:{shadowRoot:{activeElement:leaf}}}},body:{style:{overflow:"hidden"}}};assert.equal(h.deepActiveElement(),leaf);let focused=0;const replacement={getAttribute:()=>"3908809",focus(){focused++;}};card.isConnected=true;card.content.querySelectorAll=()=>[replacement];card.content.querySelector=()=>null;card._pcOverlay={hidden:false};card._pcReturnFocus={isConnected:false};card._pcFocusAthleteId="3908809";card._closePlayerCardPopup();assert.equal(focused,1);assert.equal(h.context.document.body.style.overflow,"");
});

test("four NBA quarters and overtime never infer a shootout",()=>{
  const h=harness();
  assert.equal(h.periodLabel(4),"Q4");assert.equal(h.periodLabel(5),"OT");assert.equal(h.periodLabel(6),"2OT");
  assert.equal(h.periodLabel(5,{is_shootout:true}),"OT");
});
test("halftime shows actual scoring leaders without claiming a starting lineup",()=>{
  const h=harness(),a=fixture();a.period_context.is_halftime=true;a.period_context.is_intermission=true;
  const html=cardFor(h,a,{live_default_view:"expanded"}).content.innerHTML;
  assert.match(html,/Halftime|HALF|HT/);assert.match(html,/Game Leaders/);assert.match(html,/Points/);
  assert.doesNotMatch(html,/Goalie|Power play|Saves|Starting lineup/i);
});
for(const [file,period,suffix] of [
  ["summary_401809234_regulation.json",4,""],["summary_401810626_overtime.json",5," · OT"],["summary_401810581_double_overtime.json",6," · 2OT"],
]){
  test("actual final marker "+file,()=>{
    const h=harness(),a=fixture();a.competition=JSON.parse(fs.readFileSync(path.join(__dirname,"fixtures",file),"utf8")).header.competitions[0];
    a.is_live=false;a.mode="final";a.period_context={period,display_clock:""};
    const card=cardFor(h,a),html=card.content.innerHTML;
    assert.equal(html.match(/class="compact-date compact-final-date">([^<]*)<\/div>/)[1],card.formatCompactDateTime(a.competition.date).date+suffix);
    const lines=card.renderLinescore(a.competition,null,a);assert.doesNotMatch(lines,/>SO</);
    if(period>4)assert.match(lines,new RegExp(">"+(period===5?"OT":"2OT")+"<"));
  });
}
test("status-only final period changes repaint the date marker",()=>{
  const h=harness(),a=fixture();a.is_live=false;a.mode="final";a.period_context={};
  a.competition.status={period:4,type:{state:"post",completed:true,name:"STATUS_FINAL",detail:"Final"}};
  const card=cardFor(h,a),before=card.content.innerHTML;
  a.competition.status={period:5,type:{state:"post",completed:true,name:"STATUS_FINAL",detail:"Final/OT"}};
  card.render();assert.notEqual(card.content.innerHTML,before);assert.match(card.content.innerHTML,/ · OT<\/div>/);
});
test("unknown timeout and shot clock stay unknown while valid zero renders",()=>{
  const h=harness();assert.match(h.renderSituationRow({away_timeouts:0,home_timeouts:0,shot_clock:0}),/>0</);
  assert.match(h.renderSituationRow({}),/—/);
  assert.doesNotMatch(h.renderPossessionRow({situation:{}}),/class="nba-possession"|Ball possession/i);
});
test("court and unavailable shot chart never invent a ball or shot location",()=>{
  const h=harness(),html=h.renderCourt(fixture(),[{is_shot:true,coordinate:{x:-214748340,y:-214748365}}],true);
  assert.match(html,/unavailable/i);assert.doesNotMatch(html,/-214748340|nba-court-play|puck|rink/i);
});
test("actual NBA shots use ESPN court coordinates and mirror the home side only",()=>{
  const h=harness(),a=fixture(),raw=JSON.parse(fs.readFileSync(path.join(__dirname,"fixtures/summary_401809234_regulation.json"),"utf8"));
  const plays=["4018092347","4018092348","40180923410"].map(id=>{
    const p=raw.plays.find(play=>play.id===id);
    return {id:p.id,text:p.text,coordinate:p.coordinate,team_id:p.team.id,is_shot:p.shootingPlay,points_attempted:p.pointsAttempted,scoring_play:p.scoringPlay};
  });
  const html=h.renderCourt(a,plays,true);
  assert.equal((html.match(/class="nba-court-play/g)||[]).length,3);
  assert.match(html,/cx="19\.00" cy="27\.00"[^>]*class="nba-court-play away made"/);
  assert.match(html,/cx="93\.00" cy="51\.00"[^>]*class="nba-court-play home made"/);
  assert.match(html,/class="nba-court-play away"/);
  assert.doesNotMatch(h.renderCourt(a,plays,false),/class="nba-court-play/);
  a.period_context.period=5;assert.equal(h.renderCourt(a,plays,true),html);
});
test("shot chart rejects bad coordinates, non-shots, free throws and unknown teams",()=>{
  const h=harness(),a=fixture(),base={is_shot:true,points_attempted:2,team_id:"18",coordinate:{x:25,y:10},text:"Rejected"};
  const bad=[
    ...[{x:-1,y:0},{x:51,y:0},{x:0,y:-5},{x:0,y:91},{x:NaN,y:0},{x:0,y:Infinity},{x:true,y:0},{x:"25",y:10},{x:-214748340,y:-214748365}].map(coordinate=>({...base,coordinate})),
    {...base,is_shot:false},{...base,is_free_throw:true},{...base,points_attempted:1},{...base,play_type:"Free Throw - 1 of 2"},{...base,team_id:"999"},{...base,team_id:""},
  ];
  const html=h.renderCourt(a,bad,true);assert.doesNotMatch(html,/class="nba-court-play|<title>Rejected/);assert.match(html,/Shot locations unavailable/);
  const escaped=h.renderCourt(a,[{...base,text:"Made <script>bad</script>"}],true);assert.match(escaped,/&lt;script&gt;/);assert.doesNotMatch(escaped,/<script>/);
});
test("scoring-list clicks and Space scroll normally without collapsing the card",()=>{
  const h=harness(),card=cardFor(h),panel=new h.context.Element();
  panel.closest=selector=>selector.includes(".nba-scoring-list")?panel:null;
  let prevented=0;const event={target:panel,key:" ",preventDefault(){prevented++;},stopPropagation(){}};
  card._onContentClick(event);card._onContentKeydown(event);assert.equal(prevented,0);
});
test("featured player stats use basketball scoring and rebounds",()=>{
  const h=harness(),line=h.featuredPlayerLines(fixture().featured_players.home,false);
  assert.match(line.primary+line.secondary,/23/);assert.match(line.primary+line.secondary,/PTS/);
  assert.doesNotMatch(line.primary+line.secondary,/SV|GAA|YDS|TD|INT/);
});
test("mobile stat tokens escape values and attach each bullet to the following value-label pair",()=>{
  const h=harness(),html=h.featuredStatTokens("<script>bad</script> & 31 PTS • 2 REB • 5 AST");
  assert.equal(html,'<span class="nba-stat-token">&lt;script&gt;bad&lt;/script&gt; &amp; 31 PTS</span> <span class="nba-stat-token"><span class="nba-stat-separator" aria-hidden="true">• </span>2 REB</span> <span class="nba-stat-token"><span class="nba-stat-separator" aria-hidden="true">• </span>5 AST</span>');
  assert.doesNotMatch(html,/<script>/);assert.equal(h.featuredStatTokens(""),"");
});
test("both featured players render indivisible primary and FG-three-point stat tokens",()=>{
  const h=harness(),a=fixture();a.featured_players.away.game_stats.three_pointers="2-8";a.featured_players.home.game_stats.three_pointers="2-5";
  const html=cardFor(h,a,{live_default_view:"expanded"}).content.innerHTML;
  const lines=[...html.matchAll(/<div class="matchup-subtle (strongish|secondary) stat-line">([\s\S]*?)<\/div>/g)];
  assert.equal(lines.length,4);
  const values=lines.map(line=>[...line[2].matchAll(/<span class="nba-stat-token">(?:<span class="nba-stat-separator" aria-hidden="true">• <\/span>)?([^<]*)<\/span>/g)].map(token=>token[1]));
  assert.deepEqual(values,[["31 PTS","2 REB","4 AST"],["12-25 FG","2-8 3PT"],["23 PTS","3 REB","5 AST"],["5-18 FG","2-5 3PT"]]);
  a.featured_players.home.game_stats.field_goals="<img src=x>";
  const escaped=cardFor(h,a,{live_default_view:"expanded"}).content.innerHTML;
  assert.match(escaped,/&lt;img src=x&gt; FG<\/span>/);assert.doesNotMatch(escaped,/<img src=x>/);
});
test("mobile stat wrapping stays scoped and bounded around the center court",()=>{
  const {CARD_CSS:css}=harness();
  const line=css.match(/nba-live-game-card \.matchup-side \.stat-line\s*\{([^}]*)\}/)[1];
  assert.match(line,/display:\s*flex/);assert.match(line,/flex-wrap:\s*wrap/);assert.match(line,/justify-content:\s*center/);assert.match(line,/max-width:\s*100%/);
  const token=css.match(/nba-live-game-card \.nba-stat-token\s*\{([^}]*)\}/)[1];
  assert.match(token,/white-space:\s*nowrap/);assert.match(token,/max-width:\s*100%/);assert.match(token,/overflow:\s*hidden/);assert.match(token,/text-overflow:\s*ellipsis/);
  assert.match(css,/nba-live-game-card \.matchup-side\s*\{[^}]*max-width:\s*100%/);
  assert.match(css,/nba-live-game-card [^{]*\.nba-matchup[^}]*column-gap:\s*6px/);
});
test("scoring summary includes every basket in newest-first keyboard-scrollable form",()=>{
  const h=harness(),a=fixture();a.scoring_plays=Array.from({length:94},(_,i)=>({id:String(i),period_number:4,score_value:i%3+1,away_score:100,home_score:110,text:"Basket "+String(i).padStart(2,"0")}));
  a.scoring_plays[0].text="Basket 00 <script>bad</script>";
  const before=JSON.stringify(a.scoring_plays),html=h.renderScoringPlaysPanel(a,a.away_team,a.home_team);
  assert(html.indexOf("Basket 93")<html.indexOf("Basket 00"));assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
  assert.equal(JSON.stringify(a.scoring_plays),before);assert.match(html,/role="region"/);assert.match(html,/tabindex="0"/);
  assert.match(h.CARD_CSS,/\.nba-scoring-list[^}]*max-height:\s*320px/);
});
test("game and season tables use independent machine keys and honest average labels",()=>{
  const h=harness(),team=fixture().team_stats.away;
  assert.match(h.teamStatsTablesHtml(team,"game",{}),/>31</);
  const season={"3908809":{season:"2025-26",categories:{players:{columns:["PTS","REB"],keys:["avgPoints","avgRebounds"],stats:["26.0","3.3"],descriptions:["Average points","Average rebounds"]}}}};
  const html=h.teamStatsTablesHtml(team,"season",season);assert.match(html,/26\.0/);assert.match(html,/3\.3/);assert.match(html,/2025-26/);assert.match(html,/per game/i);
  assert.match(h.teamStatsTablesHtml(team,"season",{}),/—/);
});
test("DNP badge follows did_not_play, never a stale reason on a played row",()=>{
  const h=harness(),team=fixture().team_stats.away,row=team.categories[0].rows[0];row.reason="COACH'S DECISION";row.did_not_play=false;
  assert.doesNotMatch(h.teamStatsTablesHtml(team,"game",{}),/>DNP</);
  row.did_not_play=true;assert.match(h.teamStatsTablesHtml(team,"game",{}),/DNP/);
});
test("career popup renders basketball categories and escapes labels",()=>{
  const h=harness(),html=h.playerCardBodyHtml({bio:{team:"Knicks",position:"G"},career:{label:"Per-game averages <x>",columns:["PTS"],seasons:[{year:"2026",team:"NY",stats:["26.0"]}],totals:["19.2"]}});
  assert.match(html,/Per-game averages &lt;x&gt;/);assert.match(html,/26\.0/);assert.doesNotMatch(html,/Goaltending|Saves|Pitching|Passing/);
});
