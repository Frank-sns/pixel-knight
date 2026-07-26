# Pixel Knight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a top-down 2D dungeon crawler shooter inspired by Soul Knight with 3 characters, 8 weapons × 7 affixes, 10 enemy types, 7 bosses across 3 floors, all in a single HTML file.

**Architecture:** Single HTML file with Canvas 2D rendering, requestAnimationFrame game loop, state-machine driven scenes (menu → char-select → playing → boss → victory/gameover). All game entities follow `update(dt)` / `render(ctx)` pattern. Procedural dungeon on a 4×3 grid. Web Audio API for synthesized SFX.

**Tech Stack:** HTML5 Canvas 2D, vanilla JavaScript (ES6+), Web Audio API, localStorage for high scores. Zero external dependencies. Single file: `pixel_knight.html`.

## Global Constraints

- Single HTML file `pixel_knight.html` — all CSS/JS inline
- Game resolution: 960×640 logical pixels, CSS-scaled to fit window
- 60fps target via requestAnimationFrame with delta-time capping at 100ms
- Canvas drawing only — no DOM elements for in-game UI
- Web Audio API OscillatorNode for all sounds (no audio files)
- Keyboard-only for movement (WASD), mouse for aim/shoot
- All pixel-art visuals drawn with geometric primitives (rect, circle, line)
- localStorage key prefix: `pixel_knight_`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pixel_knight.html` | Entire game: HTML shell, CSS, all JS game code |

Internal JS module structure (within the single file):

| Section | Responsibility |
|---------|---------------|
| Config | Constants, tuning values, weapon/character/enemy/affix data tables |
| State | Game state machine, shared game state object |
| Utils | Math helpers, collision detection, random, color/particle helpers |
| Camera | View transform (world → screen), screen shake |
| Map | Dungeon generation (4×3 grid), room types, corridor carving |
| Player | Movement, aiming, HP, skills, weapon slots, rendering |
| Bullets | Bullet lifecycle, movement, collision, affix effects |
| Enemies | 10 enemy types, AI behaviors, spawning |
| Bosses | 7 boss types, phase transitions, attack patterns |
| Items | Drops, pickup logic, shop inventory |
| UI | HUD (HP, coins, floor, weapons, skills, minimap), menus, screens |
| Audio | Web Audio oscillator synthesis for SFX |
| Effects | Particles, screen flash, screen shake, death effects |
| Game | init(), game loop, scene dispatch, input handling |

---

### Task 1: HTML Shell & Game Loop Foundation

**Files:**
- Create: `pixel_knight.html`

**Interfaces:**
- Produces: Canvas `#game-canvas` (960×640), `ctx` 2D context, `requestAnimationFrame` loop, delta-time `dt` (capped at 0.1s), state machine constants `STATE`, input handler `keys{}` / `mouse{}`

- [ ] **Step 1: Create HTML boilerplate with canvas**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>像素骑士 — Pixel Knight</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0a12; overflow: hidden; display: flex; justify-content: center; align-items: center; width: 100vw; height: 100vh; }
  canvas { display: block; cursor: crosshair; }
</style>
</head>
<body>
<canvas id="game-canvas"></canvas>
<script>
// === CONFIG ===
const GW = 960, GH = 640; // game resolution
const TILE = 32;          // tile size for room grid

// === STATE MACHINE ===
const STATE = { MENU: 'menu', CHAR_SELECT: 'charSelect', PLAYING: 'playing', BOSS: 'boss', SHOP: 'shop', GAMEOVER: 'gameover', VICTORY: 'victory', PAUSED: 'paused' };
let gameState = STATE.MENU;

// === CANVAS SETUP ===
const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');
canvas.width = GW;
canvas.height = GH;

function resizeCanvas() {
  const scale = Math.min(window.innerWidth / GW, window.innerHeight / GH);
  canvas.style.width = (GW * scale) + 'px';
  canvas.style.height = (GH * scale) + 'px';
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// === INPUT ===
const keys = {};
const mouse = { x: 0, y: 0, down: false, worldX: 0, worldY: 0 };
window.addEventListener('keydown', e => { keys[e.code] = true; e.preventDefault(); });
window.addEventListener('keyup', e => { keys[e.code] = false; e.preventDefault(); });
canvas.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = GW / rect.width;
  const scaleY = GH / rect.height;
  mouse.x = (e.clientX - rect.left) * scaleX;
  mouse.y = (e.clientY - rect.top) * scaleY;
});
canvas.addEventListener('mousedown', e => { if (e.button === 0) mouse.down = true; });
canvas.addEventListener('mouseup', e => { if (e.button === 0) mouse.down = false; });
canvas.addEventListener('contextmenu', e => e.preventDefault());

// === GAME LOOP ===
let lastTime = 0;
function gameLoop(timestamp) {
  requestAnimationFrame(gameLoop);
  if (lastTime === 0) lastTime = timestamp;
  let dt = (timestamp - lastTime) / 1000;
  if (dt > 0.1) dt = 0.016;
  lastTime = timestamp;
  update(dt);
  render();
}
// Stub update/render — will be filled in later tasks
function update(dt) { /* scene dispatch */ }
function render() { ctx.clearRect(0, 0, GW, GH); }

requestAnimationFrame(gameLoop);
console.log('Pixel Knight — shell ready');
</script>
</body>
</html>
```

- [ ] **Step 2: Open in browser, verify canvas fills window**

Open `pixel_knight.html` in Chrome/Edge. Verify: black background, canvas fills window, no console errors.

- [ ] **Step 3: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: HTML shell with canvas, game loop, input handling"
```

---

### Task 2: Camera System & Screen Shake

**Files:**
- Modify: `pixel_knight.html` — add camera module after input section

**Interfaces:**
- Produces: `camera = { x, y, targetX, targetY, shakeAmount, shakeDecay }`, `camera.update(dt)`, `camera.shake(amount)`, `camera.applyTransform(ctx)` / `camera.restore(ctx)`, `camera.worldToScreen(wx, wy)` / `camera.screenToWorld(sx, sy)`

- [ ] **Step 1: Add camera module**

Add after the `// === INPUT ===` block, before `// === GAME LOOP ===`:

```javascript
// === CAMERA ===
const camera = {
  x: 0, y: 0,
  targetX: 0, targetY: 0,
  shakeAmount: 0, shakeDecay: 4,
  update(dt) {
    // Smooth follow
    this.x += (this.targetX - this.x) * 8 * dt;
    this.y += (this.targetY - this.y) * 8 * dt;
    this.shakeAmount = Math.max(0, this.shakeAmount - this.shakeDecay * dt);
  },
  shake(amount) { this.shakeAmount = Math.max(this.shakeAmount, amount); },
  applyTransform(ctx) {
    ctx.save();
    let sx = this.shakeAmount * (Math.random() * 2 - 1);
    let sy = this.shakeAmount * (Math.random() * 2 - 1);
    ctx.translate(GW/2 - this.x + sx, GH/2 - this.y + sy);
  },
  restore(ctx) { ctx.restore(); },
  worldToScreen(wx, wy) {
    return {
      x: GW/2 + (wx - this.x),
      y: GH/2 + (wy - this.y)
    };
  },
  screenToWorld(sx, sy) {
    return {
      x: this.x + (sx - GW/2),
      y: this.y + (sy - GH/2)
    };
  }
};
// Update mouse world position in mousemove handler:
//   const wp = camera.screenToWorld(mouse.x, mouse.y);
//   mouse.worldX = wp.x; mouse.worldY = wp.y;
```

- [ ] **Step 2: Update mousemove handler to set world coords**

In the canvas `mousemove` listener, add: `const wp = camera.screenToWorld(mouse.x, mouse.y); mouse.worldX = wp.x; mouse.worldY = wp.y;`

- [ ] **Step 3: Use camera in render**

Update `render()`:
```javascript
function render() {
  ctx.clearRect(0, 0, GW, GH);
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, GW, GH);
  // Camera-transformed game rendering goes here
  camera.applyTransform(ctx);
  // ... draw game objects ...
  camera.restore(ctx);
  // HUD (screen-space) goes here
}
```

- [ ] **Step 4: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: camera system with smooth follow and screen shake"
```

---

### Task 3: Player Entity — Movement, Aiming, Rendering

**Files:**
- Modify: `pixel_knight.html` — add player object

**Interfaces:**
- Produces: `player = { x, y, vx, vy, speed, hp, maxHp, charClass, angle, radius, skillCooldown, skillTimer, weapons[], currentWeapon, ... }`, `player.update(dt)`, `player.render(ctx)`, `player.takeDamage(amount)`, `player.useSkill()`

- [ ] **Step 1: Define character data and create player object**

Add after camera module:

```javascript
// === CHARACTER DATA ===
const CHARACTERS = {
  knight: {
    name: '骑士', emoji: '⚔️', color: '#44aaff',
    hp: 5, speed: 200, skillName: '冲锋斩', skillCD: 10,
    description: '均衡战士，向前冲刺斩击'
  },
  mage: {
    name: '法师', emoji: '🔮', color: '#cc44ff',
    hp: 3, speed: 240, skillName: '冰霜新星', skillCD: 8,
    description: '冻结周围敌人，远程输出'
  },
  assassin: {
    name: '刺客', emoji: '🗡️', color: '#ff6644',
    hp: 4, speed: 280, skillName: '暗影步', skillCD: 12,
    description: '隐身突袭，爆发伤害×3'
  }
};

// === PLAYER ===
const player = {
  x: 0, y: 0, vx: 0, vy: 0,
  radius: 14, angle: 0,
  charClass: 'knight',
  speed: 200,
  hp: 5, maxHp: 5,
  skillTimer: 0, skillCooldown: 10,
  weapons: [], currentWeapon: 0,
  coins: 0,
  buffs: { damageMult: 1, speedMult: 1, pierce: 0, hpBonus: 0 },
  invincible: 0,
  
  init(chosenClass) {
    const data = CHARACTERS[chosenClass];
    this.charClass = chosenClass;
    this.speed = data.speed;
    this.maxHp = data.hp;
    this.hp = data.hp;
    this.skillCooldown = data.skillCD;
    this.skillTimer = 0;
    this.coins = 0;
    this.buffs = { damageMult: 1, speedMult: 1, pierce: 0, hpBonus: 0 };
    this.invincible = 0;
    this.weapons = [{ type: 'pistol', affix: null }]; // start pistol
    this.currentWeapon = 0;
  },

  update(dt) {
    // Movement
    this.vx = 0; this.vy = 0;
    if (keys['KeyW'] || keys['ArrowUp']) this.vy = -1;
    if (keys['KeyS'] || keys['ArrowDown']) this.vy = 1;
    if (keys['KeyA'] || keys['ArrowLeft']) this.vx = -1;
    if (keys['KeyD'] || keys['ArrowRight']) this.vx = 1;
    // Normalize diagonal
    if (this.vx !== 0 && this.vy !== 0) { this.vx *= 0.707; this.vy *= 0.707; }
    const spd = this.speed * this.buffs.speedMult;
    this.x += this.vx * spd * dt;
    this.y += this.vy * spd * dt;
    // Clamp to current room
    this.x = Math.max(roomBounds.x + this.radius, Math.min(roomBounds.x + roomBounds.w - this.radius, this.x));
    this.y = Math.max(roomBounds.y + this.radius, Math.min(roomBounds.y + roomBounds.h - this.radius, this.y));
    // Aiming — angle toward mouse world position
    this.angle = Math.atan2(mouse.worldY - this.y, mouse.worldX - this.x);
    // Skill cooldown
    this.skillTimer = Math.max(0, this.skillTimer - dt);
    // Invincibility
    this.invincible = Math.max(0, this.invincible - dt);
    // Camera follow
    camera.targetX = this.x;
    camera.targetY = this.y;
  },

  takeDamage(amount) {
    if (this.invincible > 0) return false;
    this.hp -= amount;
    this.invincible = 0.5;
    camera.shake(6);
    return this.hp <= 0;
  },

  useSkill() {
    if (this.skillTimer > 0) return;
    this.skillTimer = this.skillCooldown;
    // Skill effects handled per-character in update
  },

  getWeapon() {
    return this.weapons[this.currentWeapon] || null;
  },

  render(ctx) {
    if (this.invincible > 0 && Math.floor(this.invincible * 20) % 2 === 0) return; // blink
    const cd = CHARACTERS[this.charClass];
    ctx.save();
    ctx.translate(this.x, this.y);
    // Body
    ctx.fillStyle = cd.color;
    ctx.fillRect(-10, -8, 20, 16);
    // Helmet/head
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(0, -6, 8, 0, Math.PI * 2);
    ctx.fill();
    // Weapon line pointing toward mouse
    ctx.strokeStyle = '#ffcc00';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(6, 0);
    ctx.lineTo(6 + Math.cos(this.angle) * 16, Math.sin(this.angle) * 16);
    ctx.stroke();
    ctx.restore();
  }
};

// Room bounds placeholder — updated when entering a room
let roomBounds = { x: -200, y: -150, w: 400, h: 300 };
```

- [ ] **Step 2: Integrate player into game loop**

Update `update(dt)` to call `player.update(dt)` and `camera.update(dt)`.
Update `render()` to call `player.render(ctx)` inside camera transform.

- [ ] **Step 3: Test — verify player moves with WASD, aims with mouse**

Open in browser, verify:
- Player rectangle visible in center
- WASD moves player
- Player aims toward mouse cursor
- Camera follows player

- [ ] **Step 4: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: player entity with movement, aiming, rendering"
```

---

### Task 4: Weapon System — Bullets, 8 Base Weapons, 7 Affixes

**Files:**
- Modify: `pixel_knight.html` — add weapon data, bullet system

**Interfaces:**
- Produces: `WEAPONS{}` data table, `AFFIXES{}` data table, `bullets[]` array, `spawnBullet(x, y, angle, weapon, affix)` function, `switchWeapon(slot)`, weapon fire timing in player update

- [ ] **Step 1: Define weapon and affix data tables**

```javascript
// === WEAPON DATA ===
const WEAPONS = {
  pistol:   { name:'手枪', emoji:'🔫', damage:8,  fireRate:0.4, speed:500, spread:0.02, count:1, pierce:0, color:'#ffcc00', type:'hitscan' },
  smg:      { name:'冲锋枪', emoji:'🔫', damage:4,  fireRate:0.08, speed:480, spread:0.12, count:1, pierce:0, color:'#ffaa00', type:'hitscan' },
  rifle:    { name:'步枪', emoji:'🔫', damage:6,  fireRate:0.15, speed:550, spread:0.04, count:3, pierce:0, burstDelay:0.06, color:'#ff8800', type:'hitscan' },
  shotgun:  { name:'散弹枪', emoji:'💥', damage:5,  fireRate:0.7, speed:400, spread:0.18, count:5, pierce:0, color:'#ff6600', type:'hitscan' },
  laser:    { name:'激光枪', emoji:'⚡', damage:12, fireRate:0.5, speed:700, spread:0,    count:1, pierce:3, color:'#00ffcc', type:'beam' },
  bow:      { name:'弓',   emoji:'🏹', damage:15, fireRate:0.9, speed:600, spread:0.01, count:1, pierce:1, color:'#88ff44', type:'charged' },
  sword:    { name:'剑',   emoji:'🗡️', damage:10, fireRate:0.35, speed:0,   spread:0,    count:1, pierce:99, color:'#ffffff', type:'melee', arc:Math.PI },
  staff:    { name:'法杖', emoji:'🔮', damage:9,  fireRate:0.55, speed:350, spread:0.03, count:1, pierce:0, color:'#cc88ff', type:'bounce', bounces:2 }
};

// === AFFIX DATA ===
const AFFIXES = {
  fire:    { name:'火焰', emoji:'🔥', color:'#ff4400', desc:'灼烧DoT 3秒' },
  ice:     { name:'冰霜', emoji:'❄️', color:'#88ccff', desc:'减速40% 2秒' },
  lightning:{ name:'雷电', emoji:'⚡', color:'#ffdd00', desc:'击杀弹跳2个敌人' },
  poison:  { name:'剧毒', emoji:'☠️', color:'#44ff44', desc:'叠3层爆发' },
  lifesteal:{ name:'吸血', emoji:'💀', color:'#cc44cc', desc:'击杀回0.5❤️' },
  explosive:{ name:'爆炸', emoji:'💥', color:'#ff2222', desc:'命中AoE爆炸' },
  knockback:{ name:'击退', emoji:'💨', color:'#ffffff', desc:'击退敌人' }
};
```

- [ ] **Step 2: Add bullets array and fire system**

```javascript
// === BULLETS ===
let bullets = [];

function spawnBullet(x, y, angle, wType, affixKey) {
  const wData = WEAPONS[wType];
  const count = wData.count || 1;
  for (let i = 0; i < count; i++) {
    const spreadAngle = angle + (Math.random() - 0.5) * wData.spread * 2;
    bullets.push({
      x, y,
      vx: Math.cos(spreadAngle) * wData.speed,
      vy: Math.sin(spreadAngle) * wData.speed,
      weapon: wType, affix: affixKey,
      damage: wData.damage * player.buffs.damageMult,
      pierce: wData.pierce + player.buffs.pierce,
      color: affixKey ? AFFIXES[affixKey].color : wData.color,
      life: 3, // seconds max
      bounce: wData.bounces || 0,
      // Melee
      isMelee: wType === 'sword',
      arc: wData.arc || 0,
      // Beam
      isBeam: wType === 'laser',
      // Poison stack tracking
      poisonStacks: {}
    });
  }
}
```

- [ ] **Step 3: Add weapon firing timer to player**

In `player.init()`, add `this.fireTimer = 0; this.burstIndex = 0; this.burstTimer = 0;`.
In `player.update(dt)`, add firing logic:

```javascript
// Firing (in player.update)
const wp = this.getWeapon();
if (wp && mouse.down && gameState === STATE.PLAYING) {
  const wData = WEAPONS[wp.type];
  this.fireTimer -= dt;
  if (this.fireTimer <= 0) {
    this.fireTimer = wData.fireRate;
    spawnBullet(this.x, this.y, this.angle, wp.type, wp.affix);
    // Burst for rifle
    if (wData.burstDelay) {
      this.burstIndex = 1;
      this.burstTimer = wData.burstDelay;
    }
  }
  // Burst follow-up shots
  if (this.burstIndex > 0 && this.burstIndex < (wData.count || 1)) {
    this.burstTimer -= dt;
    if (this.burstTimer <= 0) {
      spawnBullet(this.x, this.y, this.angle, wp.type, wp.affix);
      this.burstIndex++;
      this.burstTimer = wData.burstDelay;
    }
  }
}
```

- [ ] **Step 4: Add bullet update/render**

```javascript
function updateBullets(dt) {
  for (let i = bullets.length - 1; i >= 0; i--) {
    const b = bullets[i];
    b.x += b.vx * dt;
    b.y += b.vy * dt;
    b.life -= dt;
    // Check room bounds, despawn
    if (b.life <= 0 || b.x < roomBounds.x - 50 || b.x > roomBounds.x + roomBounds.w + 50 ||
        b.y < roomBounds.y - 50 || b.y > roomBounds.y + roomBounds.h + 50) {
      bullets.splice(i, 1);
    }
  }
}

function renderBullets(ctx) {
  for (const b of bullets) {
    ctx.fillStyle = b.color;
    ctx.beginPath();
    ctx.arc(b.x, b.y, b.isMelee ? 0 : 3, 0, Math.PI * 2);
    ctx.fill();
    // Glow
    ctx.fillStyle = b.color.replace('ff','aa');
    ctx.beginPath();
    ctx.arc(b.x, b.y, 6, 0, Math.PI * 2);
    ctx.fill();
  }
}
```

- [ ] **Step 5: Add weapon switch — keys 1/2 and E to pickup**

```javascript
function switchWeapon(slot) {
  if (slot >= 0 && slot < player.weapons.length) {
    player.currentWeapon = slot;
    player.fireTimer = 0;
  }
}
```

In input handling, add: `if (keys['Digit1']) { keys['Digit1'] = false; switchWeapon(0); }` and same for Digit2.

- [ ] **Step 6: Test — fire bullets in all 8 directions, verify colors per affix**

Open in browser, hold mouse button, verify:
- Bullets spawn from player toward mouse
- Different weapons have different fire patterns
- Affix colors match their definition

- [ ] **Step 7: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: weapon system with 8 base types, 7 affixes, bullet lifecycle"
```

---

### Task 5: Dungeon Generation — 4×3 Grid, Rooms, Corridors

**Files:**
- Modify: `pixel_knight.html` — add map generation module

**Interfaces:**
- Produces: `generateFloor(floorNum)` → `{ rooms[], corridors[], startRoom, bossRoom, shopRoom, chestRoom }`, `Room{ x, y, w, h, type, enemies[], cleared, explored }`, `currentRoom` reference, `enterRoom(room)`

- [ ] **Step 1: Define room types and generation algorithm**

```javascript
// === MAP GENERATION ===
const ROOM_TYPE = { START: 'start', COMBAT: 'combat', CHEST: 'chest', SHOP: 'shop', BOSS: 'boss' };
const GRID_COLS = 4, GRID_ROWS = 3;
const ROOM_W = 10 * TILE, ROOM_H = 7 * TILE; // 320×224
const CORRIDOR_W = 3 * TILE;

let dungeon = null; // { rooms[], corridors[], floorNum }
let currentRoomIdx = -1;

function getRoom(id) { return dungeon?.rooms[id]; }
function getCurrentRoom() { return getRoom(currentRoomIdx); }

function generateFloor(floorNum) {
  const rooms = [];
  // Step 1: Place start room (leftmost column, random row)
  const startRow = randInt(0, GRID_ROWS - 1);
  const startRoom = {
    id: 0,
    gridX: 0, gridY: startRow,
    cx: ROOM_W/2 + TILE, cy: startRow * (ROOM_H + CORRIDOR_W) + ROOM_H/2 + TILE,
    x: TILE, y: startRow * (ROOM_H + CORRIDOR_W) + TILE,
    w: ROOM_W, h: ROOM_H,
    type: ROOM_TYPE.START, explored: true, cleared: true,
    enemies: []
  };
  rooms.push(startRoom);
  
  // Step 2: BFS-style path generation across the grid
  // Place boss room at rightmost column
  const bossRow = randInt(0, GRID_ROWS - 1);
  const bossRoom = {
    id: 0, // will reassign
    gridX: GRID_COLS - 1, gridY: bossRow,
    cx: (GRID_COLS-1) * (ROOM_W + CORRIDOR_W) + ROOM_W/2 + TILE,
    cy: bossRow * (ROOM_H + CORRIDOR_W) + ROOM_H/2 + TILE,
    x: (GRID_COLS-1) * (ROOM_W + CORRIDOR_W) + TILE,
    y: bossRow * (ROOM_H + CORRIDOR_W) + TILE,
    w: ROOM_W, h: ROOM_H,
    type: ROOM_TYPE.BOSS, explored: false, cleared: false,
    enemies: []
  };
  
  // Step 3: Generate main path from start to boss (random walk)
  let path = [{x: 0, y: startRow}];
  let cx = 0, cy = startRow;
  while (cx < GRID_COLS - 1 || cy !== bossRow) {
    if (cx < GRID_COLS - 1 && (Math.random() < 0.7 || cy === bossRow)) {
      cx++;
    } else if (cy < bossRow) {
      cy++;
    } else if (cy > bossRow) {
      cy--;
    }
    path.push({x: cx, y: cy});
  }
  
  // Step 4: Add branch rooms
  const usedCells = new Set(path.map(p => `${p.x},${p.y}`));
  const branchCells = [];
  for (let gx = 0; gx < GRID_COLS; gx++) {
    for (let gy = 0; gy < GRID_ROWS; gy++) {
      if (!usedCells.has(`${gx},${gy}`) && Math.random() < 0.35) {
        branchCells.push({x: gx, y: gy});
        usedCells.add(`${gx},${gy}`);
      }
    }
  }
  
  // Step 5: Create all rooms
  let nextId = 1;
  // Main path rooms (skip start at index 0)
  const pathRooms = [];
  for (let i = 1; i < path.length; i++) {
    const p = path[i];
    const isBoss = (p.x === GRID_COLS - 1 && p.y === bossRow);
    const room = createRoom(nextId++, p.x, p.y, isBoss ? ROOM_TYPE.BOSS : ROOM_TYPE.COMBAT);
    if (isBoss) Object.assign(room, { x: bossRoom.x, y: bossRoom.y, cx: bossRoom.cx, cy: bossRoom.cy });
    pathRooms.push(room);
  }
  
  // Branch rooms
  const branchRooms = [];
  const branchTypes = [ROOM_TYPE.CHEST, ROOM_TYPE.SHOP, ROOM_TYPE.COMBAT, ROOM_TYPE.COMBAT];
  for (let i = 0; i < branchCells.length; i++) {
    const bc = branchCells[i];
    const rType = branchTypes[i % branchTypes.length];
    branchRooms.push(createRoom(nextId++, bc.x, bc.y, rType));
  }
  
  // Merge all rooms
  rooms.push(...pathRooms, ...branchRooms);
  // If boss wasn't in path (should be), add it
  if (!rooms.find(r => r.type === ROOM_TYPE.BOSS)) {
    bossRoom.id = nextId++;
    rooms.push(bossRoom);
  }
  
  // Step 6: Build connections (corridors) between adjacent rooms
  const corridors = buildCorridors(rooms);
  
  return { rooms, corridors, floorNum, startRoomId: 0 };
}

function createRoom(id, gx, gy, type) {
  return {
    id,
    gridX: gx, gridY: gy,
    cx: gx * (ROOM_W + CORRIDOR_W) + ROOM_W/2 + TILE,
    cy: gy * (ROOM_H + CORRIDOR_W) + ROOM_H/2 + TILE,
    x: gx * (ROOM_W + CORRIDOR_W) + TILE,
    y: gy * (ROOM_H + CORRIDOR_W) + TILE,
    w: ROOM_W, h: ROOM_H,
    type, explored: false, cleared: false,
    enemies: [],
    doors: [] // {x, y, targetRoomId, direction}
  };
}

function buildCorridors(rooms) {
  const corridors = [];
  const roomMap = {};
  for (const r of rooms) roomMap[`${r.gridX},${r.gridY}`] = r;
  
  for (const r of rooms) {
    // Check 4 directions for adjacent rooms
    const dirs = [{dx:1,dy:0,dir:'right'},{dx:-1,dy:0,dir:'left'},{dx:0,dy:1,dir:'down'},{dx:0,dy:-1,dir:'up'}];
    for (const {dx, dy, dir} of dirs) {
      const nx = r.gridX + dx, ny = r.gridY + dy;
      const neighbor = roomMap[`${nx},${ny}`];
      if (neighbor && neighbor.id > r.id) { // dedupe
        corridors.push({ from: r.id, to: neighbor.id });
        // Add doors
        let doorX, doorY;
        if (dir === 'right') { doorX = r.x + r.w; doorY = r.cy; }
        else if (dir === 'left') { doorX = r.x; doorY = r.cy; }
        else if (dir === 'down') { doorX = r.cx; doorY = r.y + r.h; }
        else { doorX = r.cx; doorY = r.y; }
        r.doors.push({ x: doorX, y: doorY, targetRoomId: neighbor.id, dir });
        const oppDir = {right:'left',left:'right',up:'down',down:'up'}[dir];
        neighbor.doors.push({ x: doorX, y: doorY, targetRoomId: r.id, dir: oppDir });
      }
    }
  }
  return corridors;
}

function randInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
```

- [ ] **Step 2: Add room rendering**

```javascript
function renderRoom(ctx, room) {
  if (!room.explored) return;
  // Floor
  ctx.fillStyle = room.type === ROOM_TYPE.BOSS ? '#1a0a0a' : '#1a1a2e';
  ctx.fillRect(room.x, room.y, room.w, room.h);
  // Walls (thick borders)
  ctx.strokeStyle = room.type === ROOM_TYPE.BOSS ? '#ff333388' : '#334466';
  ctx.lineWidth = 4;
  ctx.strokeRect(room.x - 2, room.y - 2, room.w + 4, room.h + 4);
  // Floor pattern — grid lines
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 1;
  for (let tx = room.x; tx < room.x + room.w; tx += TILE) {
    for (let ty = room.y; ty < room.y + room.h; ty += TILE) {
      ctx.strokeRect(tx, ty, TILE, TILE);
    }
  }
  // Doorways
  ctx.fillStyle = '#0a0a18';
  for (const door of room.doors) {
    ctx.fillRect(door.x - 14, door.y - 14, 28, 28);
    ctx.strokeStyle = '#556677';
    ctx.strokeRect(door.x - 14, door.y - 14, 28, 28);
  }
}
```

- [ ] **Step 3: Add room transition logic**

```javascript
function enterRoom(roomId) {
  currentRoomIdx = roomId;
  const room = getCurrentRoom();
  room.explored = true;
  roomBounds = { x: room.x + 16, y: room.y + 16, w: room.w - 32, h: room.h - 32 };
  // Spawn player at door they came from, or center if first time
  player.x = room.cx;
  player.y = room.cy;
  // If combat room and not cleared, spawn enemies
  if ((room.type === ROOM_TYPE.COMBAT || room.type === ROOM_TYPE.BOSS) && !room.cleared) {
    spawnRoomEnemies(room);
  }
}

function checkDoorCollision() {
  const room = getCurrentRoom();
  if (!room) return;
  for (const door of room.doors) {
    const dx = player.x - door.x;
    const dy = player.y - door.y;
    if (Math.sqrt(dx*dx + dy*dy) < 20) {
      enterRoom(door.targetRoomId);
      return;
    }
  }
}
```

Call `checkDoorCollision()` at end of `player.update(dt)`.

- [ ] **Step 4: Integrate into game flow**

In `initGame()`: generate dungeon with `dungeon = generateFloor(1)`, then `currentRoomIdx = dungeon.startRoomId`, enter that room.

- [ ] **Step 5: Test — generate floor, move between rooms**

Open browser, verify rooms render, player can walk through doors to adjacent rooms. Check console for room data.

- [ ] **Step 6: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: dungeon generation with 4x3 grid, rooms, corridors, transitions"
```

---

### Task 6: Enemy System — 10 Types with AI

**Files:**
- Modify: `pixel_knight.html` — add enemy data and AI

**Interfaces:**
- Produces: `ENEMIES{}` data table, `enemies[]` array, `spawnEnemy(type, x, y)`, `spawnRoomEnemies(room)`, enemy `update(dt)`/`render(ctx)`/`takeDamage(amount)`, enemy-player collision, bullet-enemy collision

- [ ] **Step 1: Define enemy data**

```javascript
// === ENEMY DATA ===
const ENEMY_DATA = {
  slime:    { name:'小史莱姆', hp:8,  speed:60,  damage:1, radius:10, color:'#44cc44', floor:1, behavior:'chase', score:10, coins:1 },
  skeleton: { name:'骷髅兵',   hp:10, speed:80,  damage:1, radius:10, color:'#cccccc', floor:1, behavior:'shoot_straight', fireRate:1.5, score:15, coins:2 },
  bat:      { name:'蝙蝠',     hp:5,  speed:150, damage:1, radius:8,  color:'#8866aa', floor:1, behavior:'circle_dive', score:10, coins:1 },
  shield:   { name:'盾兵',     hp:16, speed:50,  damage:1, radius:12, color:'#888899', floor:1, behavior:'shield_front', score:20, coins:3 },
  goblin:   { name:'哥布林枪手', hp:12, speed:100, damage:1, radius:9, color:'#88aa44', floor:2, behavior:'shoot_burst', fireRate:0.8, score:20, coins:2 },
  warlock:  { name:'暗影法师', hp:14, speed:70,  damage:1, radius:10, color:'#6644aa', floor:2, behavior:'summon_track', fireRate:2, score:25, coins:3 },
  bomber:   { name:'自爆虫',   hp:10, speed:180, damage:3, radius:11, color:'#ff6622', floor:2, behavior:'kamikaze', score:20, coins:2 },
  knight_enemy:{ name:'闪电骑士', hp:18, speed:160, damage:2, radius:11, color:'#ffcc00', floor:3, behavior:'dash', score:30, coins:3 },
  beholder: { name:'眼魔',     hp:16, speed:50,  damage:1, radius:13, color:'#ff4488', floor:3, behavior:'spin_laser', fireRate:2, score:30, coins:3 },
  golem:    { name:'石像守卫', hp:25, speed:40,  damage:2, radius:15, color:'#888877', floor:3, behavior:'throw_rock', fireRate:2.5, score:35, coins:4 }
};
```

- [ ] **Step 2: Create enemy class (object factory)**

```javascript
let enemies = [];

function createEnemy(type, x, y) {
  const data = ENEMY_DATA[type];
  return {
    type, x, y, hp: data.hp, maxHp: data.hp,
    speed: data.speed, damage: data.damage, radius: data.radius,
    color: data.color, behavior: data.behavior,
    fireRate: data.fireRate || 1, fireTimer: Math.random(),
    score: data.score, coins: data.coins,
    angle: 0, state: {}, // behavior-specific state
    alive: true,
    flashTimer: 0, // white flash on damage
    
    update(dt) {
      this.fireTimer -= dt;
      this.flashTimer = Math.max(0, this.flashTimer - dt);
      const dx = player.x - this.x;
      const dy = player.y - this.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 1;
      this.angle = Math.atan2(dy, dx);
      
      switch (this.behavior) {
        case 'chase':
          if (dist < 300) { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          break;
        case 'shoot_straight':
          if (dist < 400 && dist > 60) { this.x += Math.cos(this.angle) * this.speed * 0.5 * dt; this.y += Math.sin(this.angle) * this.speed * 0.5 * dt; }
          if (dist < 350 && this.fireTimer <= 0) { this.fireTimer = this.fireRate; spawnEnemyBullet(this.x, this.y, this.angle, 250, this.damage); }
          break;
        case 'circle_dive':
          this.state.orbitAngle = (this.state.orbitAngle || 0) + 2 * dt;
          const orbitR = 80;
          if (dist < 250) {
            this.x = player.x + Math.cos(this.state.orbitAngle) * orbitR;
            this.y = player.y + Math.sin(this.state.orbitAngle) * orbitR;
          } else { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          if (dist < 100) { this.state.dive = true; }
          if (this.state.dive) { this.x += Math.cos(this.angle) * this.speed * 3 * dt; this.y += Math.sin(this.angle) * this.speed * 3 * dt; this.state.diveTimer = (this.state.diveTimer || 0) + dt; if (this.state.diveTimer > 1.5) { this.state.dive = false; this.state.diveTimer = 0; } }
          break;
        case 'shield_front':
          if (dist < 250 && dist > 50) { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          this.state.facing = this.angle;
          break;
        case 'shoot_burst':
          if (dist > 80) { // strafe
            const strafeAngle = this.angle + Math.PI/2;
            this.x += Math.cos(strafeAngle) * this.speed * dt * (Math.sin(Date.now()/1000) > 0 ? 1 : -1);
          }
          if (dist < 400 && this.fireTimer <= 0) { this.fireTimer = this.fireRate; for (let i = -1; i <= 1; i++) { spawnEnemyBullet(this.x, this.y, this.angle + i*0.1, 300, this.damage); } }
          break;
        case 'summon_track':
          if (dist < 300 && dist > 100) { this.x -= Math.cos(this.angle) * this.speed * dt; this.y -= Math.sin(this.angle) * this.speed * dt; }
          if (this.fireTimer <= 0) { this.fireTimer = this.fireRate; spawnEnemyBullet(this.x, this.y, this.angle, 180, this.damage, true); } // tracking
          break;
        case 'kamikaze':
          if (dist < 250) { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          if (dist < 20) { this.explode(); }
          break;
        case 'dash':
          if (dist < 300) {
            if (!this.state.dashing) { this.state.dashAngle = this.angle; this.state.dashTimer = 0; this.state.dashing = true; }
            this.state.dashTimer += dt;
            const dashSpd = 400;
            this.x += Math.cos(this.state.dashAngle) * dashSpd * dt;
            this.y += Math.sin(this.state.dashAngle) * dashSpd * dt;
            if (this.state.dashTimer > 1.0) { this.state.dashing = false; this.state.dashTimer = 0; }
          }
          break;
        case 'spin_laser':
          if (dist > 150) { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          if (this.fireTimer <= 0) { this.fireTimer = this.fireRate; this.state.laserAngle = (this.state.laserAngle || 0) + Math.PI/6; /* spawn radial bullets */ }
          break;
        case 'throw_rock':
          if (dist > 150) { this.x += Math.cos(this.angle) * this.speed * dt; this.y += Math.sin(this.angle) * this.speed * dt; }
          if (dist < 500 && this.fireTimer <= 0) { this.fireTimer = this.fireRate; spawnEnemyBullet(this.x, this.y, this.angle, 200, this.damage, false, true); } // parabolic
          break;
      }
    },
    
    takeDamage(amount) {
      this.hp -= amount;
      this.flashTimer = 0.1;
      if (this.hp <= 0) { this.alive = false; player.coins += this.coins; }
    },
    
    explode() {
      // AoE damage to player
      const dx = player.x - this.x, dy = player.y - this.y;
      if (Math.sqrt(dx*dx+dy*dy) < 50) player.takeDamage(this.damage);
      this.hp = 0; this.alive = false;
    },
    
    render(ctx) {
      ctx.save();
      ctx.translate(this.x, this.y);
      const col = this.flashTimer > 0 ? '#ffffff' : this.color;
      ctx.fillStyle = col;
      // Body
      ctx.fillRect(-this.radius, -this.radius, this.radius*2, this.radius*2);
      // Eyes
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(-3, -this.radius+4, 3, 3);
      ctx.fillRect(2, -this.radius+4, 3, 3);
      // Shield render for shield enemies
      if (this.behavior === 'shield_front') {
        ctx.strokeStyle = '#aaaacc';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(0, 0, this.radius+6, this.state.facing - Math.PI/3, this.state.facing + Math.PI/3);
        ctx.stroke();
      }
      // HP bar
      if (this.hp < this.maxHp) {
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(-10, -this.radius-8, 20, 3);
        ctx.fillStyle = '#00ff00';
        ctx.fillRect(-10, -this.radius-8, 20*(this.hp/this.maxHp), 3);
      }
      ctx.restore();
    }
  };
}

function spawnEnemyBullet(x, y, angle, speed, damage, tracking, parabolic) {
  enemyBullets.push({ x, y, vx: Math.cos(angle)*speed, vy: Math.sin(angle)*speed, damage, tracking, parabolic, life: 4 });
}

let enemyBullets = [];

function spawnRoomEnemies(room) {
  enemies = enemies.filter(e => e.alive); // keep existing
  const count = 2 + Math.floor(Math.random() * 3) + dungeon.floorNum; // 3-6 per room
  const validTypes = Object.keys(ENEMY_DATA).filter(t => ENEMY_DATA[t].floor <= dungeon.floorNum);
  for (let i = 0; i < count; i++) {
    const type = validTypes[randInt(0, validTypes.length - 1)];
    const ex = room.x + 40 + Math.random() * (room.w - 80);
    const ey = room.y + 40 + Math.random() * (room.h - 80);
    enemies.push(createEnemy(type, ex, ey));
  }
}
```

- [ ] **Step 3: Add collision detection**

```javascript
function checkBulletEnemyCollisions() {
  for (let bi = bullets.length - 1; bi >= 0; bi--) {
    const b = bullets[bi];
    for (const enemy of enemies) {
      if (!enemy.alive) continue;
      const dx = b.x - enemy.x, dy = b.y - enemy.y;
      const dist = Math.sqrt(dx*dx + dy*dy);
      if (dist < enemy.radius + 4) {
        // Shield check
        if (enemy.behavior === 'shield_front') {
          const hitAngle = Math.atan2(dy, dx);
          let angleDiff = hitAngle - enemy.state.facing;
          while (angleDiff > Math.PI) angleDiff -= Math.PI*2;
          while (angleDiff < -Math.PI) angleDiff += Math.PI*2;
          if (Math.abs(angleDiff) < Math.PI/2.5) continue; // blocked by shield
        }
        enemy.takeDamage(b.damage);
        if (b.pierce <= 0) { bullets.splice(bi, 1); break; }
        else b.pierce--;
      }
    }
  }
}

function checkEnemyPlayerCollision(dt) {
  if (player.invincible > 0) return;
  for (const enemy of enemies) {
    if (!enemy.alive) continue;
    const dx = player.x - enemy.x, dy = player.y - enemy.y;
    if (Math.sqrt(dx*dx+dy*dy) < player.radius + enemy.radius) {
      player.takeDamage(enemy.damage);
    }
  }
}
```

- [ ] **Step 4: Add update/render for enemies and enemy bullets**

In `update(dt)`: `enemies.forEach(e => e.update(dt)); enemies = enemies.filter(e => e.alive);` + `enemyBullets.forEach(eb => { eb.x += eb.vx*dt; eb.y += eb.vy*dt; eb.life -= dt; }); enemyBullets = enemyBullets.filter(eb => eb.life > 0);`

In `render(ctx)`: render enemies and enemy bullets.

- [ ] **Step 5: Room cleared check**

```javascript
// After updating enemies, check if room is cleared
const room = getCurrentRoom();
if (room && room.type === ROOM_TYPE.COMBAT && !room.cleared && enemies.filter(e=>e.alive).length === 0) {
  room.cleared = true;
  // Drop item chance
  if (Math.random() < 0.4) spawnDrop(room.cx, room.cy);
}
```

- [ ] **Step 6: Test — enemies spawn, move, attack, take damage, die**

Open browser, enter a combat room, verify enemies appear with correct behaviors per type.

- [ ] **Step 7: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: 10 enemy types with AI behaviors, enemy bullets, collision"
```

---

### Task 7: Boss System — 7 Bosses with Unique Mechanics

**Files:**
- Modify: `pixel_knight.html` — add boss data and boss-specific AI

**Interfaces:**
- Produces: `BOSSES{}` data table, `currentBoss` reference, `startBossFight(bossType)`, boss object with phases, attack patterns

- [ ] **Step 1: Define boss data**

```javascript
// === BOSS DATA ===
const BOSS_DATA = {
  goblin_king: {
    name:'哥布林王', floor:1, hp:80, radius:24, color:'#88aa22',
    phases: [{ threshold:1.0, attacks:['summon','bomb','charge'], moveSpeed:60 }]
  },
  spider_queen: {
    name:'蛛后', floor:1, hp:70, radius:22, color:'#8844aa',
    phases: [{ threshold:1.0, attacks:['web','spawn_spiders','ground_pound'], moveSpeed:80 }]
  },
  magma_dragon: {
    name:'熔岩巨龙', floor:2, hp:120, radius:28, color:'#ff4422',
    phases: [
      { threshold:1.0, attacks:['fire_cone','tail_swipe','dive'], moveSpeed:50 },
      { threshold:0.5, attacks:['fire_tracking','tail_swipe','dive'], moveSpeed:70 }
    ]
  },
  shadow_twins: {
    name:'暗影双子', floor:2, hp:90, radius:16, color:'#664488',
    phases: [
      { threshold:1.0, attacks:['twin_slash','twin_bolts'], moveSpeed:90 },
      { threshold:0.5, attacks:['twin_slash','twin_bolts_enraged'], moveSpeed:130 }
    ]
  },
  vine_behemoth: {
    name:'藤蔓巨兽', floor:2, hp:100, radius:26, color:'#44aa44',
    phases: [{ threshold:1.0, attacks:['tentacle','spore_cloud','thorn_ring'], moveSpeed:0 }]
  },
  thousand_eye: {
    name:'千眼魔', floor:3, hp:130, radius:20, color:'#ff4488',
    phases: [{ threshold:1.0, attacks:['spin_lasers','eye_minions','flash_blind'], moveSpeed:50 }]
  },
  thunder_lord: {
    name:'雷霆领主', floor:3, hp:110, radius:18, color:'#ffdd00',
    phases: [{ threshold:1.0, attacks:['flash_strike','lightning_pillar','dash_combo'], moveSpeed:200 }]
  },
  ancient_golem: {
    name:'远古石像', floor:3, hp:150, radius:30, color:'#888877',
    phases: [
      { threshold:1.0, attacks:['rock_throw','ground_slam','stone_wall'], moveSpeed:30 },
      { threshold:0.5, attacks:['rock_throw_fast','ground_slam','stone_wall'], moveSpeed:50 }
    ]
  },
  shadow_lord: {
    name:'暗影领主', floor:3, hp:200, radius:26, color:'#220022',
    phases: [
      { threshold:1.0, attacks:['bullet_hell','teleport'], moveSpeed:70 },
      { threshold:0.66, attacks:['clone','cross_laser'], moveSpeed:90 },
      { threshold:0.33, attacks:['bullet_hell','fire_aura'], moveSpeed:140 }
    ]
  }
};

// Boss buff drops per floor
const BOSS_BUFFS = [
  [{ name:'生命上限+1', apply:()=>{ player.maxHp+=1; player.hp=Math.min(player.hp+1,player.maxHp); }},
   { name:'移速+15%', apply:()=>{ player.buffs.speedMult+=0.15; }}],
  [{ name:'伤害+15%', apply:()=>{ player.buffs.damageMult+=0.15; }},
   { name:'射速+10%', apply:()=>{ /* reduces fireRate globally */ }},
   { name:'击杀回血', apply:()=>{ player.buffs.lifesteal=(player.buffs.lifesteal||0)+1; }}],
  [{ name:'伤害+20%', apply:()=>{ player.buffs.damageMult+=0.20; }},
   { name:'生命上限+1', apply:()=>{ player.maxHp+=1; player.hp+=1; }},
   { name:'弹幕穿透+1', apply:()=>{ player.buffs.pierce+=1; }}]
];
```

- [ ] **Step 2: Create boss object factory**

```javascript
let boss = null;
let bossBullets = [];
// Boss attack helper arrays
let bossClones = [];        // shadow_lord clones
let tentacleZones = [];    // vine_behemoth tentacles
let sporeZones = [];       // vine_behemoth spores
let lightningPillars = []; // thunder_lord pillars
let stoneWalls = [];       // ancient_golem walls

function startBossFight(bossType) {
  const data = BOSS_DATA[bossType];
  boss = {
    type: bossType, name: data.name,
    x: getCurrentRoom().cx, y: getCurrentRoom().cy - 60,
    hp: data.hp, maxHp: data.hp,
    radius: data.radius, color: data.color,
    speed: data.phases[0].moveSpeed,
    phase: 0, phases: data.phases,
    attackTimer: 0, attackCooldown: 1.5,
    currentAttack: null, attackState: {},
    angle: 0, alive: true,
    flashTimer: 0,
    
    update(dt) {
      this.flashTimer = Math.max(0, this.flashTimer - dt);
      this.attackTimer -= dt;
      // Phase check
      const hpRatio = this.hp / this.maxHp;
      for (let i = this.phases.length-1; i >= 0; i--) {
        if (hpRatio <= this.phases[i].threshold && i >= this.phase) { this.phase = i; this.speed = this.phases[i].moveSpeed; }
      }
      // Move toward player (unless stationary boss like vine_behemoth)
      if (this.speed > 0) {
        const dx = player.x - this.x, dy = player.y - this.y;
        const dist = Math.sqrt(dx*dx+dy*dy) || 1;
        this.angle = Math.atan2(dy, dx);
        if (dist > 100) { this.x += Math.cos(this.angle)*this.speed*dt; this.y += Math.sin(this.angle)*this.speed*dt; }
      }
      // Pick and execute attack
      if (this.attackTimer <= 0) { this.pickAttack(); }
      this.executeAttack(dt);
    },
    
    pickAttack() {
      const attacks = this.phases[this.phase].attacks;
      this.currentAttack = attacks[randInt(0, attacks.length-1)];
      this.attackTimer = 2 + Math.random() * 2;
      this.attackState = { elapsed: 0 };
    },
    
    executeAttack(dt) {
      this.attackState.elapsed += dt;
      const t = this.attackState.elapsed;
      const a = this.currentAttack;
      // === Shared attack patterns ===
      if (a === 'bullet_hell') { /* spiral bullet pattern */ if (t < 2 && Math.floor(t*10)%2===0) { for(let i=0;i<16;i++){ const ang=(i/16)*Math.PI*2+t; spawnBossBullet(this.x,this.y,ang,200,1,'#ff4444'); } } }
      if (a === 'charge' && t < 2) { this.x += Math.cos(this.angle)*300*dt; this.y += Math.sin(this.angle)*300*dt; }
      if (a === 'bomb' && Math.floor(t*2)%2===0 && t<3) { for(let i=0;i<5;i++){ spawnBossBullet(this.x,this.y,this.angle+i*0.4-1,150,1,'#ff8800'); } }
      if (a === 'fire_cone' && t<2) { if(Math.floor(t*10)%2===0){ for(let i=-3;i<=3;i++){ spawnBossBullet(this.x,this.y,this.angle+i*0.15,220+t*40,1,'#ff4400'); } } }
      if (a === 'tail_swipe' && t>0.3 && t<0.8) { /* melee AoE around boss */ const dx=player.x-this.x,dy=player.y-this.y; if(Math.sqrt(dx*dx+dy*dy)<60)player.takeDamage(2); }
      if (a === 'dive') { if(t<0.8){this.y-=300*dt;}else if(t<1.5){this.y+=600*dt;if(t>1.2&&Math.sqrt((player.x-this.x)**2+(player.y-this.y)**2)<80)player.takeDamage(2);} }
      if (a === 'summon' && t>0.5 && !this.attackState.summoned) { this.attackState.summoned=true; for(let i=0;i<4;i++){ enemies.push(createEnemy('slime',this.x+(Math.random()-0.5)*100,this.y+(Math.random()-0.5)*100)); } }
      if (a === 'teleport' && t>0.8 && !this.attackState.teleported) { this.attackState.teleported=true; this.x=player.x+(Math.random()-0.5)*200; this.y=player.y+(Math.random()-0.5)*200; }
      if (a === 'ground_pound' && t>1 && t<1.3) { camera.shake(8); if(Math.sqrt((player.x-this.x)**2+(player.y-this.y)**2)<100)player.takeDamage(1); }
      if (a === 'spawn_spiders' && t>0.6 && !this.attackState.spawned) { this.attackState.spawned=true; for(let i=0;i<6;i++){ enemies.push(createEnemy('bat',this.x+(Math.random()-0.5)*120,this.y+(Math.random()-0.5)*120)); } }
      // === Shadow Lord attacks ===
      if (a === 'clone' && t>0.5 && !this.attackState.cloned) {
        this.attackState.cloned = true;
        for (let i=0; i<3; i++) {
          const cx = this.x + (Math.random()-0.5)*200;
          const cy = this.y + (Math.random()-0.5)*200;
          bossClones.push({ x:cx, y:cy, life:5, color:this.color, alpha:0.5, radius:this.radius*0.8 });
        }
      }
      if (a === 'cross_laser' && t<3) {
        this.attackState.laserRot = (this.attackState.laserRot||0) + 1.5*dt;
        const a0 = this.attackState.laserRot;
        for (let i=0; i<4; i++) {
          const la = a0 + i*Math.PI/2;
          // Check if player is on the laser line (within 10px of the infinite line through boss)
          const pdx = player.x-this.x, pdy = player.y-this.y;
          const proj = Math.abs(-Math.sin(la)*pdx + Math.cos(la)*pdy);
          if (proj < 15 && Math.sqrt(pdx*pdx+pdy*pdy) < 400) player.takeDamage(1);
          // Render hint: draw laser line (handled in boss render)
        }
      }
      if (a === 'fire_aura' && t>0) {
        if (Math.sqrt((player.x-this.x)**2+(player.y-this.y)**2) < 70) player.takeDamage(0.5);
      }
      // === Spider Queen attacks ===
      if (a === 'web' && t>0.3 && !this.attackState.webDone) {
        this.attackState.webDone = true;
        spawnBossBullet(this.x, this.y, this.angle, 300, 0, '#cccccc');
        // Web bullet applies slow on hit (handled in collision)
      }
      // === Vine Behemoth attacks ===
      if (a === 'tentacle' && t<2) {
        if (Math.floor(t*6)%3===0 && !this.attackState['tent'+Math.floor(t*6)]) {
          const idx = Math.floor(t*6);
          this.attackState['tent'+idx] = true;
          const tx = this.x + (Math.random()-0.5)*250;
          const ty = this.y + (Math.random()-0.5)*200;
          tentacleZones.push({ x:tx, y:ty, timer:1.0, radius:20 });
          if (Math.sqrt((player.x-tx)**2+(player.y-ty)**2) < 30) player.takeDamage(1);
        }
      }
      if (a === 'spore_cloud' && t<3) {
        if (Math.floor(t*3) !== this.attackState.lastSpore) {
          this.attackState.lastSpore = Math.floor(t*3);
          sporeZones.push({ x:player.x+(Math.random()-0.5)*80, y:player.y+(Math.random()-0.5)*80, life:4, radius:35 });
        }
      }
      if (a === 'thorn_ring' && t<2) {
        const ringR = 80 + t*120;
        const thornCount = 24;
        for (let i=0; i<thornCount; i++) {
          const ta = (i/thornCount)*Math.PI*2 + t;
          const tx = this.x + Math.cos(ta)*ringR;
          const ty = this.y + Math.sin(ta)*ringR;
          // Check player proximity
          if (Math.sqrt((player.x-tx)**2+(player.y-ty)**2) < 16) player.takeDamage(1);
        }
      }
      // === Thousand Eye attacks ===
      if (a === 'spin_lasers' && t<3) {
        this.attackState.spinAngle = (this.attackState.spinAngle||0) + 3*dt;
        for (let i=0; i<8; i++) {
          const la = this.attackState.spinAngle + i*Math.PI/4;
          if (Math.floor(t*10)%2===0) spawnBossBullet(this.x, this.y, la, 180, 1, '#ff4488');
        }
      }
      if (a === 'flash_blind' && t>0.5 && !this.attackState.blinded) {
        this.attackState.blinded = true;
        flashScreen(0.4); // white screen flash blinds player
      }
      // === Eye minions ===
      if (a === 'eye_minions' && t>0.3 && !this.attackState.minionsSpawned) {
        this.attackState.minionsSpawned = true;
        for (let i=0; i<6; i++) {
          enemies.push(createEnemy('bat', this.x+(Math.random()-0.5)*120, this.y+(Math.random()-0.5)*120));
        }
      }
      // === Thunder Lord attacks ===
      if (a === 'flash_strike' && t>0.4 && !this.attackState.struck) {
        this.attackState.struck = true;
        this.x = player.x; this.y = player.y;
        camera.shake(10);
        if (Math.sqrt((player.x-this.x)**2+(player.y-this.y)**2) < 50) player.takeDamage(2);
      }
      if (a === 'lightning_pillar' && t<3) {
        if (Math.floor(t*4) !== this.attackState.lastPillar) {
          this.attackState.lastPillar = Math.floor(t*4);
          const px = player.x + (Math.random()-0.5)*150;
          const py = player.y + (Math.random()-0.5)*150;
          lightningPillars.push({ x:px, y:py, life:2.0, radius:25 });
        }
      }
      if (a === 'dash_combo' && t<3) {
        if (Math.floor(t*2) !== this.attackState.lastDash) {
          this.attackState.lastDash = Math.floor(t*2);
          this.state.dashAngle = this.angle;
          this.state.dashTimer = 0;
        }
        this.x += Math.cos(this.state.dashAngle||this.angle)*450*dt;
        this.y += Math.sin(this.state.dashAngle||this.angle)*450*dt;
        if (Math.sqrt((player.x-this.x)**2+(player.y-this.y)**2) < 30) player.takeDamage(2);
      }
      // === Ancient Golem attacks ===
      if (a === 'rock_throw') {
        if (Math.floor(t*3)%2===0&&t<3) spawnBossBullet(this.x, this.y, this.angle, 300, 2, '#888888', true);
      }
      if (a === 'rock_throw_fast') {
        if (Math.floor(t*5)%2===0&&t<2) spawnBossBullet(this.x, this.y, this.angle, 350, 2, '#888888', true);
      }
      if (a === 'ground_slam' && t>0.8 && t<1.5) {
        for (let i=0; i<5; i++) {
          const sw = this.x+(i-2)*60;
          if (Math.abs(player.y-this.y) < 30 && Math.abs(player.x-sw) < 30) player.takeDamage(2);
        }
        camera.shake(6);
      }
      if (a === 'stone_wall' && t>0.5 && !this.attackState.wallSpawned) {
        this.attackState.wallSpawned = true;
        for (let i=-1; i<=1; i+=2) {
          stoneWalls.push({ x:player.x+i*80, y:player.y, life:4, w:20, h:80 });
        }
      }
    },
    
    takeDamage(amount) {
      this.hp -= amount;
      this.flashTimer = 0.08;
      if (this.hp <= 0) { this.alive = false; }
    },
    
    render(ctx) {
      const col = this.flashTimer > 0 ? '#ffffff' : this.color;
      ctx.fillStyle = col;
      ctx.fillRect(this.x-this.radius, this.y-this.radius, this.radius*2, this.radius*2);
      // Boss HP bar (top of screen, screen-space)
    }
  };
  gameState = STATE.BOSS;
}
```

- [ ] **Step 2 (continued): Add boss bullet and collision**

```javascript
function spawnBossBullet(x, y, angle, speed, damage, color, parabolic) {
  bossBullets.push({ x, y, vx: Math.cos(angle)*speed, vy: Math.sin(angle)*speed, damage, color, parabolic, life: 5 });
}

// In update loop: bossBullets update, bossBullet-player collision
```

- [ ] **Step 3: Boss defeat → drop buff, progress**

```javascript
function onBossDefeated() {
  const room = getCurrentRoom();
  room.cleared = true;
  const defeatedBossType = boss.type;
  const isFinalBoss = (defeatedBossType === 'shadow_lord');
  
  // Drop buff based on floor (non-final bosses only)
  if (!isFinalBoss) {
    const floorBuffs = BOSS_BUFFS[dungeon.floorNum - 1] || [];
    if (floorBuffs.length > 0) {
      const buff = floorBuffs[randInt(0, floorBuffs.length-1)];
      buff.apply();
      showMessage(`获得 Buff: ${buff.name}`, 3000);
    }
  }
  // Drop weapon
  spawnRandomWeapon(room.cx, room.cy);
  // Drop health
  spawnDrop(room.cx - 30, room.cy, 'heart');
  
  // Clean up boss state
  boss = null;
  bossBullets = [];
  bossClones = [];
  tentacleZones = [];
  sporeZones = [];
  lightningPillars = [];
  stoneWalls = [];
  
  if (isFinalBoss) {
    gameState = STATE.VICTORY;
    saveHighScore();
    SFX.bossExplosion();
  } else {
    gameState = STATE.PLAYING;
    // Check if all non-start/non-boss rooms cleared → advance floor hint
  }
}
```

- [ ] **Step 4: Test — trigger boss fight, verify unique attack patterns**

- [ ] **Step 5: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: 7 boss types with multi-phase AI, attack patterns, buff drops"
```

---

### Task 8: Items, Drops & Shop System

**Files:**
- Modify: `pixel_knight.html` — add drop items and shop

**Interfaces:**
- Produces: `drops[]` array, `spawnDrop(x, y, type)`, `spawnRandomWeapon(x, y)`, `pickupItem(item)`, shop room interaction

- [ ] **Step 1: Create drop system**

```javascript
let drops = []; // { x, y, type, data, life }

function spawnDrop(x, y, type) {
  const item = { x, y, type, life: 30 }; // despawn after 30s
  if (type === 'heart') { item.emoji = '❤️'; item.color = '#ff4444'; }
  else if (type === 'coin_pile') { item.emoji = '💰'; item.amount = 5+randInt(0,10); item.color = '#ffdd00'; }
  else if (type === 'energy') { item.emoji = '⚡'; item.color = '#44aaff'; }
  else if (type === 'weapon') { /* filled by spawnRandomWeapon */ }
  drops.push(item);
}

function spawnRandomWeapon(x, y) {
  const wTypes = Object.keys(WEAPONS);
  const wType = wTypes[randInt(0, wTypes.length-1)];
  const hasAffix = Math.random() < 0.6;
  const affix = hasAffix ? Object.keys(AFFIXES)[randInt(0, Object.keys(AFFIXES).length-1)] : null;
  drops.push({
    x, y, type: 'weapon',
    weaponType: wType,
    affix,
    emoji: WEAPONS[wType].emoji,
    color: affix ? AFFIXES[affix].color : WEAPONS[wType].color,
    life: 30,
    name: `${affix ? AFFIXES[affix].name : ''}${WEAPONS[wType].name}`
  });
}

function pickupItem(item) {
  switch (item.type) {
    case 'heart':
      player.hp = Math.min(player.maxHp, player.hp + 1);
      break;
    case 'coin_pile':
      player.coins += item.amount;
      break;
    case 'energy':
      player.skillTimer = Math.max(0, player.skillTimer - player.skillCooldown * 0.5);
      break;
    case 'weapon':
      // Add to weapon slots or replace current
      if (player.weapons.length < 2) {
        player.weapons.push({ type: item.weaponType, affix: item.affix });
      } else {
        player.weapons[player.currentWeapon] = { type: item.weaponType, affix: item.affix };
      }
      break;
  }
}
```

- [ ] **Step 2: Add E key pickup logic**

In update, check distance from player to each drop. If close + E pressed, call `pickupItem()` and remove drop.

- [ ] **Step 3: Shop room interaction**

```javascript
// When player enters a SHOP room and presses E near shopkeeper NPC:
function openShop() {
  gameState = STATE.SHOP;
  // Shop items generated per floor
  shopItems = [
    { type:'heart', name:'血包', price:10, emoji:'❤️' },
    { type:'weapon', name:'普通武器', price:30, weaponType:Object.keys(WEAPONS)[randInt(0,7)], affix:null, emoji:'🔫' },
    { type:'weapon', name:'附魔武器', price:60, weaponType:Object.keys(WEAPONS)[randInt(0,7)], affix:Object.keys(AFFIXES)[randInt(0,6)], emoji:'✨' },
    { type:'energy', name:'技能重置', price:15, emoji:'⚡' }
  ];
}
```

- [ ] **Step 4: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: item drops, weapon pickups, shop system"
```

---

### Task 9: Full UI — HUD, Minimap, Menus, Screens

**Files:**
- Modify: `pixel_knight.html` — add all UI rendering and menu screens

**Interfaces:**
- Produces: `renderHUD(ctx)`, `renderMinimap(ctx)`, `renderMenu(ctx)`, `renderCharSelect(ctx)`, `renderGameOver(ctx)`, `renderVictory(ctx)`, menu input handling

- [ ] **Step 1: Render HUD (screen space, after camera.restore)**

```javascript
function renderHUD(ctx) {
  // Top bar
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(0, 0, GW, 44);
  
  // HP hearts
  ctx.font = '20px monospace';
  for (let i = 0; i < player.maxHp; i++) {
    ctx.fillText(i < player.hp ? '❤️' : '🖤', 12 + i * 28, 30);
  }
  
  // Coins & floor
  ctx.fillStyle = '#ffdd00';
  ctx.fillText(`💰 ${player.coins}`, 12 + player.maxHp * 28 + 20, 30);
  ctx.fillStyle = '#aaccff';
  ctx.fillText(`第${dungeon?.floorNum || '?'}层`, GW - 150, 30);
  
  // Bottom bar
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(0, GH - 60, GW, 60);
  
  // Current weapon
  const wp = player.getWeapon();
  if (wp) {
    const wData = WEAPONS[wp.type];
    const affixName = wp.affix ? AFFIXES[wp.affix].name : '';
    ctx.fillStyle = wp.affix ? AFFIXES[wp.affix].color : '#ffffff';
    ctx.fillText(`[1] ${affixName}${wData.name} ${wData.emoji}`, 16, GH - 30);
  }
  // Second weapon
  if (player.weapons.length > 1 && player.currentWeapon !== 1) {
    const wp2 = player.weapons[1];
    const wData2 = WEAPONS[wp2.type];
    const affixName2 = wp2.affix ? AFFIXES[wp2.affix].name : '';
    ctx.fillText(`[2] ${affixName2}${wData2.name} ${wData2.emoji}`, 16, GH - 10);
  }
  
  // Skill status
  const cd = CHARACTERS[player.charClass];
  const ready = player.skillTimer <= 0;
  ctx.fillStyle = ready ? '#00ff88' : '#ff4444';
  ctx.fillText(`[Space] ${cd.skillName} ${ready ? '✅' : Math.ceil(player.skillTimer)+'s'}`, GW - 250, GH - 20);
}
```

- [ ] **Step 2: Render minimap**

```javascript
function renderMinimap(ctx) {
  if (!dungeon) return;
  const mmX = GW - 150, mmY = 50, mmW = 135, mmH = 105;
  ctx.fillStyle = 'rgba(0,0,0,0.7)';
  ctx.fillRect(mmX, mmY, mmW, mmH);
  ctx.strokeStyle = '#334466';
  ctx.strokeRect(mmX, mmY, mmW, mmH);
  
  const cellW = mmW / GRID_COLS, cellH = mmH / GRID_ROWS;
  for (const room of dungeon.rooms) {
    const rx = mmX + room.gridX * cellW + 2;
    const ry = mmY + room.gridY * cellH + 2;
    if (room.explored) {
      ctx.fillStyle = room.type === ROOM_TYPE.BOSS ? '#ff3333' :
                      room.type === ROOM_TYPE.SHOP ? '#ffcc00' :
                      room.type === ROOM_TYPE.CHEST ? '#44ccff' : '#445566';
      ctx.fillRect(rx, ry, cellW - 4, cellH - 4);
    }
    if (room.id === currentRoomIdx) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.strokeRect(rx - 1, ry - 1, cellW - 2, cellH - 2);
    }
  }
}
```

- [ ] **Step 3: Menu, character select, game over screens**

```javascript
function renderMenu(ctx) {
  ctx.fillStyle = '#0a0a12';
  ctx.fillRect(0, 0, GW, GH);
  // Title
  ctx.font = 'bold 56px monospace';
  ctx.fillStyle = '#ffcc00';
  ctx.textAlign = 'center';
  ctx.fillText('像 素 骑 士', GW/2, 180);
  ctx.font = '18px monospace';
  ctx.fillStyle = '#667788';
  ctx.fillText('Pixel Knight — 地牢探索射击', GW/2, 220);
  // Play button
  ctx.fillStyle = '#00aacc';
  ctx.fillRect(GW/2 - 100, 300, 200, 50);
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 22px monospace';
  ctx.fillText('开 始 游 戏', GW/2, 333);
  // High score
  const hs = localStorage.getItem('pixel_knight_highscore') || 0;
  ctx.font = '16px monospace';
  ctx.fillStyle = '#888888';
  ctx.fillText(`最高分: ${hs}`, GW/2, 400);
  ctx.textAlign = 'start';
}

function renderCharSelect(ctx) {
  ctx.fillStyle = '#0a0a12';
  ctx.fillRect(0, 0, GW, GH);
  ctx.font = 'bold 32px monospace';
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.fillText('选择角色', GW/2, 80);
  // 3 character cards
  const chars = Object.entries(CHARACTERS);
  chars.forEach(([key, data], i) => {
    const cx = GW/4 * (i+1);
    const cy = 350;
    ctx.fillStyle = 'rgba(20,20,40,0.9)';
    ctx.fillRect(cx-80, cy-70, 160, 180);
    ctx.strokeStyle = data.color;
    ctx.lineWidth = 2;
    ctx.strokeRect(cx-80, cy-70, 160, 180);
    ctx.font = '40px monospace';
    ctx.fillText(data.emoji, cx, cy-30);
    ctx.font = 'bold 18px monospace';
    ctx.fillStyle = data.color;
    ctx.fillText(data.name, cx, cy+10);
    ctx.font = '13px monospace';
    ctx.fillStyle = '#888888';
    ctx.fillText(`❤️ x${data.hp}`, cx, cy+35);
    ctx.fillText(`技能: ${data.skillName}`, cx, cy+55);
    ctx.fillText(`${data.description}`, cx, cy+75);
  });
  ctx.textAlign = 'start';
}

function renderGameOver(ctx) {
  ctx.fillStyle = 'rgba(0,0,0,0.7)';
  ctx.fillRect(0, 0, GW, GH);
  ctx.font = 'bold 48px monospace';
  ctx.fillStyle = '#ff4444';
  ctx.textAlign = 'center';
  ctx.fillText('阵 亡', GW/2, 250);
  ctx.font = '18px monospace';
  ctx.fillStyle = '#aaaaaa';
  ctx.fillText(`到达: 第${dungeon?.floorNum||1}层 | 金币: ${player.coins}`, GW/2, 310);
  ctx.fillText('按 Enter 返回菜单', GW/2, 380);
  ctx.textAlign = 'start';
}

function renderVictory(ctx) {
  ctx.fillStyle = 'rgba(0,0,0,0.7)';
  ctx.fillRect(0, 0, GW, GH);
  ctx.font = 'bold 48px monospace';
  ctx.fillStyle = '#ffdd00';
  ctx.textAlign = 'center';
  ctx.fillText('🏆 胜 利 🏆', GW/2, 250);
  ctx.font = '18px monospace';
  ctx.fillStyle = '#aaaaaa';
  ctx.fillText(`击败了暗影领主! 金币: ${player.coins}`, GW/2, 310);
  ctx.fillText('按 Enter 返回菜单', GW/2, 380);
  ctx.textAlign = 'start';
}
```

- [ ] **Step 4: Menu input handling**

In update, dispatch by state:
- MENU: click detection on play button → transition to CHAR_SELECT
- CHAR_SELECT: click on character card → `player.init(chosenClass); initGame(); gameState = STATE.PLAYING`
- GAMEOVER/VICTORY: Enter → gameState = STATE.MENU
- PLAYING/BOSS/SHOP: Tab → toggle minimap expanded; Esc → PAUSED

- [ ] **Step 5: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: complete UI — HUD, minimap, menu, char select, game over, victory screens"
```

---

### Task 10: Audio — Web Audio API Sound Effects

**Files:**
- Modify: `pixel_knight.html` — add audio module

**Interfaces:**
- Produces: `SFX` object with methods `shoot()`, `hit()`, `enemyDeath()`, `bossExplosion()`, `pickup()`, `menuSelect()`, `skill()`, `doorOpen()`, `bossMusic()`

- [ ] **Step 1: Create audio context and SFX functions**

```javascript
// === AUDIO ===
let audioCtx = null;
function getAudioCtx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return audioCtx;
}

const SFX = {
  play(freq, duration, type, volume, ramp) {
    try {
      const ctx = getAudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type || 'square';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(volume || 0.1, ctx.currentTime);
      if (ramp) gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      else gain.gain.linearRampToValueAtTime(0, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + duration);
    } catch(e) { /* audio not supported */ }
  },
  
  shoot() { this.play(800, 0.05, 'square', 0.05); },
  hit() { this.play(200, 0.08, 'sawtooth', 0.08, true); },
  enemyDeath() { this.play(150, 0.15, 'triangle', 0.06, true); },
  bossExplosion() {
    this.play(60, 0.5, 'sawtooth', 0.15, true);
    setTimeout(() => this.play(40, 0.4, 'square', 0.1, true), 200);
  },
  pickup() { this.play(600, 0.06, 'sine', 0.08); setTimeout(() => this.play(900, 0.06, 'sine', 0.08), 60); },
  menuSelect() { this.play(440, 0.1, 'sine', 0.1); setTimeout(() => this.play(660, 0.1, 'sine', 0.1), 80); },
  skill() { this.play(300, 0.2, 'triangle', 0.12); setTimeout(() => this.play(500, 0.15, 'triangle', 0.1), 100); },
  doorOpen() { this.play(250, 0.12, 'sine', 0.06); },
  damage() { this.play(100, 0.1, 'sawtooth', 0.12, true); }
};
```

- [ ] **Step 2: Wire SFX into game events**

- Call `SFX.shoot()` when player fires
- Call `SFX.hit()` when bullet hits enemy
- Call `SFX.enemyDeath()` when enemy dies
- Call `SFX.bossExplosion()` when boss dies
- Call `SFX.pickup()` when picking up items
- Call `SFX.menuSelect()` on menu clicks
- Call `SFX.skill()` on skill use
- Call `SFX.damage()` on player damage

- [ ] **Step 3: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: Web Audio API synthesized sound effects"
```

---

### Task 11: Polish — Particles, Effects, & Floor Progression

**Files:**
- Modify: `pixel_knight.html` — add particle system, floor transitions, final polish

**Interfaces:**
- Produces: `particles[]` array, `spawnParticles(x, y, color, count)`, floor transition effects, screen flash, score tracking

- [ ] **Step 1: Particle system**

```javascript
let particles = [];

function spawnParticles(x, y, color, count) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 50 + Math.random() * 200;
    particles.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0.3 + Math.random() * 0.5,
      maxLife: 0.3 + Math.random() * 0.5,
      color, radius: 1 + Math.random() * 3
    });
  }
}

function updateParticles(dt) {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.life -= dt;
    if (p.life <= 0) particles.splice(i, 1);
  }
}

function renderParticles(ctx) {
  for (const p of particles) {
    const alpha = p.life / p.maxLife;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = p.color;
    ctx.fillRect(p.x - p.radius, p.y - p.radius, p.radius*2, p.radius*2);
  }
  ctx.globalAlpha = 1;
}
```

- [ ] **Step 2: Wire particles to game events**

- Enemy death → `spawnParticles(enemy.x, enemy.y, enemy.color, 8)`
- Boss death → `spawnParticles(boss.x, boss.y, boss.color, 30)`
- Player damage → `spawnParticles(player.x, player.y, '#ff4444', 5)`
- Pickup → `spawnParticles(item.x, item.y, item.color, 5)`

- [ ] **Step 3: Floor progression**

```javascript
function advanceFloor() {
  if (dungeon.floorNum >= 3) {
    // Final boss already defeated → victory
    gameState = STATE.VICTORY;
    return;
  }
  // Screen flash white
  flashScreen(0.5);
  // Generate next floor
  dungeon = generateFloor(dungeon.floorNum + 1);
  currentRoomIdx = dungeon.startRoomId;
  enterRoom(currentRoomIdx);
  // Full heal
  player.hp = player.maxHp;
  // Keep buffs, weapons, coins
}
```

- [ ] **Step 4: Screen flash effect**

```javascript
let screenFlash = 0;
function flashScreen(duration) { screenFlash = duration; }

// In render(), after camera.restore:
if (screenFlash > 0) {
  ctx.fillStyle = `rgba(255,255,255,${screenFlash})`;
  ctx.fillRect(0, 0, GW, GH);
  screenFlash -= dt;
}
```

- [ ] **Step 5: Score tracking and saving**

```javascript
function getScore() {
  return player.coins * 10 + (player.maxHp * 50) + (dungeon ? dungeon.floorNum * 200 : 0);
}
function saveHighScore() {
  const score = getScore();
  const prev = parseInt(localStorage.getItem('pixel_knight_highscore') || '0');
  if (score > prev) localStorage.setItem('pixel_knight_highscore', score.toString());
}
```

Call `saveHighScore()` on game over and victory.

- [ ] **Step 6: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: particles, screen effects, floor progression, score tracking"
```

---

### Task 12: Integration, Balancing & Final Testing

**Files:**
- Modify: `pixel_knight.html` — integration pass, tuning, bug fixes

**Interfaces:**
- Consumes: All modules from Tasks 1-11
- Produces: Complete, playable game

- [ ] **Step 1: Full game flow integration**

Verify the complete flow works:
1. Menu → Character Select → Game Start
2. Floor 1: rooms + enemies → Boss → advance
3. Floor 2: rooms + harder enemies → 2 Bosses → advance
4. Floor 3: rooms + hardest enemies → 2 Bosses + Shadow Lord → Victory
5. Death → Game Over → high score save

- [ ] **Step 2: Tuning pass**

Adjust these values based on play-testing:
- Enemy HP/damage per floor
- Weapon damage values
- Boss HP scaling
- Coin drop rates
- Shop prices

```javascript
// Tuning constants (add to CONFIG section)
const TUNING = {
  enemyHpScale: [1.0, 1.4, 2.0],    // per floor
  enemyDmgScale: [1.0, 1.3, 1.8],
  bossHpScale: [1.0, 1.5, 2.2],
  dropChanceWeapon: 0.35,
  dropChanceHeart: 0.20,
  coinDropMin: 1, coinDropMax: 3,
};
```

- [ ] **Step 3: Edge case testing**

- Player at 0 HP → game over trigger
- All weapons tested (fire, switch, affix effects visible)
- Room transitions with enemies alive → doors lock until cleared
- Boss room → doors lock, clear on kill
- Shop → buy with insufficient coins (should be blocked)
- Full inventory → pickup replaces current weapon
- Pause during boss fight → resume works
- Minimap updates on room transitions

- [ ] **Step 4: Browser compatibility check**

Test in Chrome, Edge, Firefox — verify Canvas renders correctly, audio plays, input works.

- [ ] **Step 5: Commit**

```bash
git add pixel_knight.html
git commit -m "feat: final integration, balancing, edge case fixes"
```

---

## Implementation Order

Tasks should be executed sequentially (1→12) as each depends on the previous. The single file grows with each task — each commit adds a self-contained module to `pixel_knight.html`.

**Estimated total effort:** ~12 tasks, 30-60 min each = 6-12 hours

**Testing strategy:** After each task, open in browser and verify the feature works before committing. Game is self-testing — no automated test suite for a Canvas game.
