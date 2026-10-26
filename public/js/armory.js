// The locker: your soldier on the left, the kit of the class you are looking at down
// the right, a tab for each class across the top. Press a slot (primary, secondary,
// perk, grenade, knife, skin, cart) and the chooser opens in its place: the things you
// can carry, the finishes you own, the attachments you have unlocked. Everything you
// pick shows on the soldier behind, who is the game's own menu scene.

import { locker, CRATES } from './locker.js';
import { FINISHES, FINISH, OUTFITS, OUTFIT, CARTS, CART, CART_FACTORY } from './skins.js';
import { WEAPONS, LOADOUTS, PERKS, NADE_INFO, SECONDARIES, nadesFor } from './weapons.js';
import { settings, saveSettings, keyName } from './settings.js';
import { ATTACHMENTS, slotsFor, slotList, nextUnlock } from './attachments.js';
import { uiBlip } from './audio.js';
import { esc } from './hud.js';
import { gunStats, openGunStats } from './gunstats.js';
import { tileHTML, FACTORY_BG } from './lockerui.js';

const $ = (id) => document.getElementById(id);

let ld = 0;            // the class on show
let slot = null;       // the chooser that is open, or null for the slot list
let hooks = {};        // onLoadout(i), onCrates(), onClose(), onChange()
let wired = false;

const GUN_BLURB = {
  smg: '30 rounds, fast and steady', pdw: '17 rounds gone in under a second, brutal up close', carbine: '30 rounds, the all-rounder',
  lmg: '100 rounds, heavy and slow to reload', shotgun: 'Pump action, nine pellets a shell', flamer: 'Six metres of fire',
  sniper: 'Bolt action, 6× scope, one headshot', heavy: 'One round, one kill, slow and loud',
  pistol: '12 rounds, quick and light', revolver: 'Six rounds, long reach, three to kill',
};
const SLOT_NAMES = { primary: 'Primary', secondary: 'Secondary', perk: 'Perk', nade: 'Grenade', knife: 'Knife', skin: 'Skin', cart: 'Cart' };

// -- what each slot holds right now ----------------------------------------------------

function finishName(weapon, finish) {
  return finish && FINISH[finish] ? FINISH[finish].name : 'Factory';
}

function slotValue(id) {
  const L = LOADOUTS[ld];
  if (id === 'primary') {
    const w = locker.primaryFor(ld);
    const fit = locker.attachFor(w);
    const n = Object.values(fit).filter((v) => v && v !== 'none').length;
    return { name: WEAPONS[w].name, sub: `${finishName(w, locker.equippedGun(w))}${n ? ` · ${n} attachment${n > 1 ? 's' : ''}` : ''}`, swatch: swatchOf(w, locker.equippedGun(w)) };
  }
  if (id === 'secondary') {
    const w = locker.secondaryFor(ld);
    const f = w === 'revolver' ? locker.equippedGun('revolver') : locker.equippedPistol(ld);
    return { name: WEAPONS[w].name, sub: finishName(w, f), swatch: swatchOf(w, f) };
  }
  if (id === 'perk') {
    const p = PERKS[locker.perkFor(ld)];
    return { name: p.name, sub: p.uses ? `${p.uses} per life` : p.blurb.split('. ')[0], swatch: '' };
  }
  if (id === 'nade') {
    const k = locker.nadeFor(ld);
    return { name: NADE_INFO[k].name, sub: `${nadesFor(ld, k)} per life`, swatch: '' };
  }
  if (id === 'knife') {
    const f = locker.equippedGun('knife');
    return { name: WEAPONS.knife.name, sub: finishName('knife', f), swatch: swatchOf('knife', f) };
  }
  if (id === 'skin') {
    const o = locker.equippedOutfit();
    return { name: OUTFIT[o] ? OUTFIT[o].name : 'Standard', sub: 'Outfit', swatch: OUTFIT[o] ? swatchHTML({ kind: 'outfit', outfit: o }) : '' };
  }
  if (id === 'cart') {
    const c = locker.equippedCart();
    return { name: (CART[c] || CART_FACTORY).name, sub: 'Golf cart', swatch: swatchHTML({ kind: 'cart', cart: c }) };
  }
  return { name: '', sub: '', swatch: '' };
}

function swatchOf(weapon, finish) {
  return finish && FINISH[finish] ? swatchHTML({ kind: 'gun', weapon, finish }) : `<div class="am-swatch" style="background:${FACTORY_BG}"></div>`;
}

function swatchHTML(sel) {
  // the tile's swatch alone, lifted from the locker's tile
  const html = tileHTML(sel);
  const m = html.match(/<div class="sk-swatch" style="background:([^"]*)"><\/div>/);
  return `<div class="am-swatch" style="background:${m ? m[1] : '#444'}"></div>`;
}

// -- the slot list -----------------------------------------------------------------------

function renderSlots(host) {
  const L = LOADOUTS[ld];
  const head = document.createElement('div');
  head.className = 'am-class';
  head.innerHTML = `<h2>${esc(L.title)}</h2><p>${esc(L.blurb)}</p>`;
  host.appendChild(head);
  for (const id of ['primary', 'secondary', 'perk', 'nade', 'knife', 'skin', 'cart']) {
    const v = slotValue(id);
    const b = document.createElement('button');
    b.className = 'am-slot';
    b.innerHTML = `${v.swatch || '<div class="am-swatch am-none"></div>'}<div class="am-slot-text"><div class="am-slot-label">${SLOT_NAMES[id]}</div>` +
      `<div class="am-slot-name">${esc(v.name)}</div><div class="am-slot-sub">${esc(v.sub)}</div></div><div class="am-chev">›</div>`;
    b.addEventListener('click', () => { slot = id; uiBlip(); render(); });
    host.appendChild(b);
  }
}

// -- the choosers ------------------------------------------------------------------------

function choiceRow(host, items, cur, onPick) {
  const row = document.createElement('div');
  row.className = 'am-choices';
  for (const it of items) {
    const b = document.createElement('button');
    b.className = 'am-choice' + (it.id === cur ? ' on' : '') + (it.locked ? ' locked' : '');
    b.innerHTML = `<b>${esc(it.name)}</b><small>${esc(it.sub || '')}</small>${it.id === cur ? '<i>Equipped</i>' : ''}`;
    if (it.locked) b.disabled = true;
    else b.addEventListener('click', () => { onPick(it.id); uiBlip(); render(); });
    row.appendChild(b);
  }
  host.appendChild(row);
}

function heading(host, title, sub) {
  const h = document.createElement('div');
  h.className = 'am-sec';
  h.innerHTML = `<span>${esc(title)}</span><small>${esc(sub || '')}</small>`;
  host.appendChild(h);
}

function finishGrid(host, weapon, current, onPick) {
  const order = FINISHES.map((f) => f.id);
  const owned = locker.gunSkins(weapon).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const grid = document.createElement('div');
  grid.className = 'am-grid';
  const mk = (finish) => {
    const b = document.createElement('button');
    const on = (finish || null) === (current || null);
    b.className = 'sk small' + (on ? ' equipped' : '');
    b.innerHTML = finish ? tileHTML({ kind: 'gun', weapon, finish }, on ? '<div class="sk-eq">On</div>' : '')
      : `<div class="sk-swatch" style="background:${FACTORY_BG}"></div><div class="sk-name">Factory</div><div class="sk-sub">${WEAPONS[weapon].short}</div><div class="sk-rarity">Default</div>${on ? '<div class="sk-eq">On</div>' : ''}`;
    b.addEventListener('click', () => { onPick(finish); uiBlip(); render(); });
    return b;
  };
  grid.appendChild(mk(null));
  for (const f of owned) grid.appendChild(mk(f));
  host.appendChild(grid);
  if (!owned.length) {
    const hint = document.createElement('div');
    hint.className = 'am-hint';
    hint.textContent = weapon === 'knife' ? 'Open Blade Crates to find knife finishes.' : `Open crates to find ${WEAPONS[weapon].short} finishes.`;
    host.appendChild(hint);
  }
}

function attachRows(host, weapon, note) {
  if (!ATTACHMENTS[weapon]) return;
  const kills = locker.killsWith(weapon);
  const next = nextUnlock(weapon, kills);
  const line = next ? `${kills} kills · ${next.left} more to unlock ${next.items.map((i) => i.name).join(', ')}` : `${kills} kills · everything unlocked`;
  heading(host, 'Attachments', note ? `${line} · ${note}` : line);
  const fitted = locker.attachFor(weapon);
  const st = gunStats(weapon, fitted);
  const by = Object.fromEntries(st.rows.map((r) => [r.k, r.text]));
  const sum = document.createElement('div');
  sum.className = 'am-gunline';
  sum.innerHTML = `<span>Damage <b>${esc(by.dmg)}</b></span><span>Fire rate <b>${esc(by.rpm)}</b></span><span>Hip <b>${esc(by.hip || '—')}</b></span><span>Aimed <b>${esc(by.ads || '—')}</b></span><span>Reload <b>${esc(by.reload || '—')}</b></span>`;
  const more = document.createElement('button');
  more.className = 'btn small ghost';
  more.textContent = 'All gun stats';
  more.addEventListener('click', () => { uiBlip(); openGunStats(weapon, { changed: () => {}, closed: () => render() }); });
  sum.appendChild(more);
  host.appendChild(sum);
  for (const s of slotsFor(weapon)) {
    const row = document.createElement('div');
    row.className = 'at-row';
    row.innerHTML = `<div class="at-slot">${esc(s.name)}</div>`;
    const items = document.createElement('div');
    items.className = 'at-items';
    for (const a of slotList(weapon, s.id)) {
      const locked = kills < a.unlock;
      const on = fitted[s.id] === a.id;
      const b = document.createElement('button');
      b.className = 'at' + (on ? ' on' : '') + (locked ? ' locked' : '');
      b.innerHTML = `<div class="at-name">${esc(a.name)}</div><div class="at-sub">${esc(a.blurb)}</div>` + (locked ? `<div class="at-lock">${a.unlock} kills</div>` : on ? '<div class="at-on">Fitted</div>' : '');
      b.disabled = locked;
      if (!locked) b.addEventListener('click', () => { locker.setAttach(weapon, s.id, a.id); uiBlip(); render(); });
      items.appendChild(b);
    }
    row.appendChild(items);
    host.appendChild(row);
  }
}

function renderChooser(host) {
  const L = LOADOUTS[ld];
  const back = document.createElement('button');
  back.className = 'am-back';
  back.innerHTML = `‹ <span>${esc(L.title)}</span> · ${SLOT_NAMES[slot]}`;
  back.addEventListener('click', () => { slot = null; uiBlip(); render(); });
  host.appendChild(back);
  const body = document.createElement('div');
  body.className = 'am-body';
  host.appendChild(body);
  if (slot === 'primary') {
    const w = locker.primaryFor(ld);
    heading(body, 'Gun', L.weapons.length > 1 ? 'Pick what this class carries' : 'What this class carries');
    choiceRow(body, L.weapons.map((id) => ({ id, name: WEAPONS[id].name, sub: GUN_BLURB[id] || '' })), w, (id) => locker.setPrimary(ld, id));
    heading(body, 'Finish', `${WEAPONS[w].short} skins you own`);
    finishGrid(body, w, locker.equippedGun(w), (f) => locker.equipGun(w, f));
    attachRows(body, w);
  } else if (slot === 'secondary') {
    const w = locker.secondaryFor(ld);
    heading(body, 'Sidearm', 'The same choice for every class, remembered per class');
    choiceRow(body, SECONDARIES.map((id) => ({ id, name: WEAPONS[id].name, sub: GUN_BLURB[id] || '' })), w, (id) => locker.setSecondary(ld, id));
    heading(body, 'Finish', `${WEAPONS[w].short} skins you own`);
    if (w === 'revolver') finishGrid(body, 'revolver', locker.equippedGun('revolver'), (f) => locker.equipGun('revolver', f));
    else finishGrid(body, 'pistol', locker.equippedPistol(ld), (f) => locker.equipPistol(ld, f));
    attachRows(body, w, 'These follow you to every class');
  } else if (slot === 'perk') {
    const cur = locker.perkFor(ld);
    heading(body, 'Perk', `Use it with ${keyName(settings.binds.perk)}`);
    choiceRow(body, L.perks.map((id) => {
      const u = PERKS[id].unlock, locked = !locker.perkUnlocked(id);
      return { id, name: PERKS[id].name, locked, sub: locked ? `${u.kills} ${WEAPONS[u.weapon].short.toLowerCase()} kills to unlock · you have ${locker.killsWith(u.weapon)}` : PERKS[id].uses ? `${PERKS[id].uses} per life · ${PERKS[id].blurb}` : PERKS[id].blurb };
    }), cur, (id) => locker.setPerk(ld, id));
  } else if (slot === 'nade') {
    const kinds = L.nadeKinds || ['frag'];
    const cur = locker.nadeFor(ld);
    heading(body, 'Grenade', `${nadesFor(ld, cur)} per life`);
    choiceRow(body, kinds.map((k) => ({ id: k, name: NADE_INFO[k].name, sub: NADE_INFO[k].blurb })), cur, (k) => locker.setNade(ld, k));
  } else if (slot === 'knife') {
    heading(body, 'Knife', `Two hits up close · draw it with ${keyName(settings.binds.melee)}`);
    finishGrid(body, 'knife', locker.equippedGun('knife'), (f) => locker.equipGun('knife', f));
  } else if (slot === 'skin') {
    heading(body, 'Outfit', `${locker.outfits().length} of ${locker.outfitTotal()} collected`);
    const grid = document.createElement('div');
    grid.className = 'am-grid';
    const eq = locker.equippedOutfit();
    const ord = OUTFITS.map((o) => o.id);
    for (const o of locker.outfits().sort((a, b) => ord.indexOf(a) - ord.indexOf(b))) {
      const b = document.createElement('button');
      b.className = 'sk small' + (o === eq ? ' equipped' : '');
      b.innerHTML = tileHTML({ kind: 'outfit', outfit: o }, o === eq ? '<div class="sk-eq">On</div>' : '');
      b.addEventListener('click', () => { locker.equipOutfit(o); uiBlip(); render(); });
      grid.appendChild(b);
    }
    body.appendChild(grid);
  } else if (slot === 'cart') {
    heading(body, 'Golf cart', locker.carts().length ? `${locker.carts().length} of ${locker.cartTotal()} collected` : `Open Pit Lane Crates to find cart skins`);
    const grid = document.createElement('div');
    grid.className = 'am-grid';
    const eq = locker.equippedCart();
    const ord = CARTS.map((c) => c.id);
    for (const id of ['', ...locker.carts().sort((a, b) => ord.indexOf(a) - ord.indexOf(b))]) {
      const b = document.createElement('button');
      b.className = 'sk small' + (id === eq ? ' equipped' : '');
      b.innerHTML = tileHTML({ kind: 'cart', cart: id }, id === eq ? '<div class="sk-eq">On</div>' : '');
      b.addEventListener('click', () => { locker.equipCart(id); uiBlip(); render(); });
      grid.appendChild(b);
    }
    body.appendChild(grid);
  }
}

// -- the screen ---------------------------------------------------------------------------

// the class tabs are made once; a redraw only changes what they say, so a tab under the
// pointer is never swapped out between the press and the release
function buildTabs() {
  const tabs = $('am-classes');
  if (tabs.childElementCount) return;
  LOADOUTS.forEach((L, i) => {
    const b = document.createElement('button');
    b.className = 'am-tab';
    b.dataset.ld = i;
    b.innerHTML = `<span class="am-tab-n">${i + 1}</span><span class="am-tab-name">${esc(L.title)}</span><span class="am-tab-gun"></span><span class="am-inuse">In use</span>`;
    b.addEventListener('click', () => {
      if (ld === i && !slot) return;
      ld = i;
      slot = null;
      settings.lastLoadout = i;
      saveSettings();
      render();
      uiBlip();
      if (hooks.onLoadout) setTimeout(() => hooks.onLoadout(i), 0);
    });
    tabs.appendChild(b);
  });
}

let refreshTimer = null;
function render() {
  const inUse = settings.lastLoadout || 0;
  buildTabs();
  for (const b of $('am-classes').children) {
    const i = Number(b.dataset.ld);
    b.classList.toggle('on', i === ld);
    b.querySelector('.am-tab-gun').textContent = WEAPONS[locker.primaryFor(i)].short;
    b.querySelector('.am-inuse').hidden = i !== inUse;
  }
  const side = $('am-side');
  const keep = side.scrollTop;
  side.innerHTML = '';
  if (slot) renderChooser(side); else renderSlots(side);
  side.scrollTop = slot ? keep : 0;
  $('am-dinars').textContent = locker.dinars;
  const accountsOn = !$('account-strip').classList.contains('no-accounts');
  $('am-saved').textContent = locker.signedIn ? 'Saved to your account' : accountsOn ? 'Saved in this browser · sign in to keep it everywhere' : 'Saved in this browser';
  // the soldier catches up once the screen has drawn: his gun is baked, which takes a moment
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => { if (hooks.onChange) hooks.onChange(ld); }, 30);
}

function wire() {
  if (wired) return;
  wired = true;
  $('am-close').addEventListener('click', closeArmory);
  $('am-crates').addEventListener('click', () => { uiBlip(); if (hooks.onCrates) hooks.onCrates(); });
  locker.onChange(() => { if (!$('armory').hidden) render(); });
  document.addEventListener('keydown', (e) => {
    if ($('armory').hidden || e.code !== 'Escape') return;
    if (slot) { slot = null; render(); } else closeArmory();
  });
}

export function openArmory(h = {}) {
  wire();
  hooks = h;
  ld = settings.lastLoadout || 0;
  slot = null;
  $('armory').hidden = false;
  render();
}

export function armoryOpen() {
  return !$('armory').hidden;
}

export function closeArmory() {
  if ($('armory').hidden) return;
  $('armory').hidden = true;
  if (hooks.onClose) hooks.onClose();
}
