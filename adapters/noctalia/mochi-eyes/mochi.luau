--!nonstrict
-- Mochi Eyes: a low-power, bar-only companion with original anime-inspired moments.

local speed = noctalia.getConfig("animation_speed") or "lively"
local audioReactive = noctalia.getConfig("audio_spectrum") == true
local activityAware = noctalia.getConfig("activity_awareness") ~= false
local animeEnabled = noctalia.getConfig("anime_moments") ~= false
local gifEnabled = noctalia.getConfig("gif_moments") ~= false
local momentFrequency = noctalia.getConfig("moment_frequency") or "balanced"
local tickMs = if speed == "hyper" then 750 elseif speed == "calm" then 3000 else 1500
local animationTickMs = if speed == "hyper" then 100 elseif speed == "calm" then 220 else 160

noctalia.setUpdateInterval(tickMs)

local expressions = {
  neutral = { "●", "●", "#FFFFFF" },
  blink = { "━", "━", "#FFFFFF" },
  ["look-left"] = { "◉", "●", "#53C7FF" },
  ["look-right"] = { "●", "◉", "#53C7FF" },
  happy = { "⌒", "⌒", "#53C7FF" },
  love = { "♥", "♥", "#53C7FF" },
  sleepy = { "—", "—", "#FFFFFF" },
  angry = { "◣", "◢", "#53C7FF" },
  sad = { "╯", "╰", "#FFFFFF" },
  surprised = { "○", "○", "#53C7FF" },
  wink = { "⌒", "●", "#53C7FF" },
  focused = { "▰", "▰", "#FFFFFF" },
}

local animeModes = {}
local gifModes = {}
local nonGifModes = {}
local catalogText = noctalia.readFile("anime_modes.json")
if catalogText ~= nil then
  local catalog = noctalia.json.decode(catalogText)
  if type(catalog) == "table" then
    if type(catalog.frames) == "table" then
      for name, frame in pairs(catalog.frames) do
        if type(frame) == "table" and #frame >= 2 then expressions[name] = frame end
      end
    end
    if type(catalog.modes) == "table" then
      animeModes = catalog.modes
      for _, mode in ipairs(animeModes) do
        if type(mode) == "table" and type(mode.animation_frames) == "table" then
          table.insert(gifModes, mode)
        else
          table.insert(nonGifModes, mode)
        end
      end
    end
  end
end

local mood = "neutral"
local moodTitle = "neutral"
local currentMode = nil
local currentFrames = nil
local frameIndex = 1
local sequenceIndex = 1
local modeTicks = 0
local temporaryTicks = 0
local tick = 0
local nextBlink = 2 + math.floor(math.random() * 3)
local activityPollTicks = math.max(1, math.floor(10000 / tickMs))
local pointerInside = false
local audioCooldown = 0

local function nextMomentDelay()
  if momentFrequency == "frequent" then return 4 + math.floor(math.random() * 5) end
  if momentFrequency == "calm" then return 16 + math.floor(math.random() * 15) end
  return 8 + math.floor(math.random() * 9)
end

local nextMoment = nextMomentDelay()

local function render()
  local pretty = moodTitle:gsub("-", " ")
  local rowProps = {
    gap = 52,
    align = "center",
    justify = "center",
    fill = "#000000",
    radius = 12,
    paddingH = 0,
    paddingV = 0,
    minWidth = 220,
    minHeight = 36,
    tooltip = "Mochi: " .. pretty .. " · click for love · right-click for anger · middle-click to sleep",
  }

  if currentFrames ~= nil then
    barWidget.render(ui.row(rowProps, {
      ui.image({ path = currentFrames[frameIndex], width = 220, height = 36, fit = "contain", radius = 12, tooltip = pretty }),
    }))
    return
  end

  local expression = expressions[mood] or expressions.neutral
  local defaultEyeColor = "#FFFFFF"
  local eyeColor = expression[3] or defaultEyeColor
  barWidget.render(ui.row(rowProps, {
    ui.label({ text = expression[1], color = eyeColor, fontSize = 30, fontWeight = "bold", baseline = "inkCentered" }),
    ui.label({ text = expression[2], color = eyeColor, fontSize = 30, fontWeight = "bold", baseline = "inkCentered" }),
  }))
end

local function clearMode()
  if currentFrames ~= nil then noctalia.setUpdateInterval(tickMs) end
  currentMode = nil
  currentFrames = nil
  frameIndex = 1
  sequenceIndex = 1
  modeTicks = 0
end

local function show(name, durationTicks, title)
  if expressions[name] == nil then name = "neutral" end
  clearMode()
  mood = name
  moodTitle = title or name
  temporaryTicks = durationTicks or 0
  render()
end

local function temporary(name, milliseconds, title)
  show(name, math.max(1, math.floor(milliseconds / tickMs)), title)
end

local function activateMode(mode)
  if type(mode) ~= "table" or type(mode.sequence) ~= "table" or #mode.sequence == 0 then return false end
  currentMode = mode
  sequenceIndex = 1
  currentFrames = if gifEnabled and type(mode.animation_frames) == "table" then mode.animation_frames else nil
  modeTicks = if currentFrames ~= nil then #currentFrames else #mode.sequence
  temporaryTicks = 0
  moodTitle = tostring(mode.title or mode.id or "anime moment")
  frameIndex = 1
  if currentFrames ~= nil then noctalia.setUpdateInterval(animationTickMs) end
  mood = tostring(mode.sequence[1] or "neutral")
  render()
  return true
end

local function chooseAnimeMoment()
  if not animeEnabled or #animeModes == 0 then return false end
  local pool = nonGifModes
  if gifEnabled and #gifModes > 0 and math.random() < 0.2 then
    pool = gifModes
  elseif #nonGifModes == 0 then
    pool = animeModes
  end
  return activateMode(pool[1 + math.floor(math.random() * #pool)])
end

local function advanceAnimation()
  if currentMode == nil then return end
  modeTicks -= 1
  if modeTicks <= 0 then
    clearMode()
    mood = "neutral"
    moodTitle = "neutral"
    nextMoment = nextMomentDelay()
    render()
    return
  end
  if currentFrames ~= nil then
    frameIndex = frameIndex + 1
    render()
    return
  end
  sequenceIndex = (sequenceIndex % #currentMode.sequence) + 1
  mood = tostring(currentMode.sequence[sequenceIndex] or "neutral")
  render()
end

local function randomIdleGesture()
  local roll = math.floor(math.random() * 6)
  if roll == 0 then temporary("look-left", 1500)
  elseif roll == 1 then temporary("look-right", 1500)
  elseif roll == 2 then temporary("wink", 1500)
  elseif roll == 3 then temporary("happy", 1500)
  elseif roll == 4 then temporary("surprised", 1500)
  else temporary("sleepy", 3000) end
end

local function inspectFocusedApp()
  if not activityAware or not noctalia.commandExists("niri") then return end
  noctalia.runAsync({ "niri", "msg", "--json", "focused-window" }, function(result)
    if result.exitCode ~= 0 or result.stdout == nil then return end
    local value = noctalia.json.decode(result.stdout)
    if type(value) ~= "table" then return end
    local title = string.lower(tostring(value.title or "") .. " " .. tostring(value.app_id or ""))
    if title:find("code", 1, true) or title:find("terminal", 1, true)
        or title:find("codex", 1, true) or title:find("studio", 1, true) then
      temporary("focused", 3000, "training focus")
    elseif title:find("youtube", 1, true) or title:find("spotify", 1, true)
        or title:find("music", 1, true) then
      temporary("happy", 3000, "music episode")
    end
  end, 450)
end

render()

function update()
  tick += 1
  if audioCooldown > 0 then audioCooldown -= 1 end

  if temporaryTicks > 0 then
    temporaryTicks -= 1
    if temporaryTicks == 0 then
      mood = "neutral"
      moodTitle = "neutral"
      render()
    end
  elseif currentMode ~= nil then
    advanceAnimation()
  elseif not pointerInside then
    nextBlink -= 1
    nextMoment -= 1
    if nextBlink <= 0 then
      temporary("blink", 1500)
      nextBlink = 2 + math.floor(math.random() * 3)
    elseif nextMoment <= 0 then
      if not chooseAnimeMoment() then randomIdleGesture() end
      nextMoment = nextMomentDelay()
    end
  end

  if currentFrames == nil and tick % activityPollTicks == 0 then inspectFocusedApp() end
end

function onHover(entered)
  pointerInside = entered
  if entered then temporary("surprised", 3000, "noticed you") else temporary("happy", 1500, "happy farewell") end
end

function onClick()
  temporary("love", 3000, "love confession")
end

function onRightClick()
  temporary("angry", 1500, "rival challenge")
end

function onMiddleClick()
  temporary("sleepy", 3000, "sleepy episode")
end

function onScroll(axis, steps, startsGesture)
  if steps < 0 then temporary("look-left", 1500) else temporary("look-right", 1500) end
end

function onAudioSpectrum(valuesCsv, stateCsv)
  if not audioReactive or audioCooldown > 0 then return end
  local first = tonumber((valuesCsv or ""):match("^[^,]+")) or 0
  if first > 0.18 then
    audioCooldown = 2
    temporary("happy", 1500, "music power-up")
  end
end

function onIpc(event, payload)
  if expressions[event] then
    temporary(event, tonumber(payload) or 3000)
    return
  end
  local requested = if event == "mode" then payload else event
  if requested == nil then return end
  for _, mode in ipairs(animeModes) do
    if mode.id == requested then activateMode(mode) return end
  end
  if event == "random" then chooseAnimeMoment() end
end
