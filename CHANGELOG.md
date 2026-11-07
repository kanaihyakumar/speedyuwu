# Changelog

## Version 3.0.0 - Easy Games, Maths Lab & Media (November 7, 2026)

### 🎮 Games are now one word (breaking change)
- Removed game IDs and `sgame create/join/start/move/...`. Start any game with one word (`sguess`, `sttt`, `swordle`, ...) or use `splay` for a dropdown menu
- Moves are plain chat: type `23` to guess, `5` to place a mark, `a` for a hangman letter, `crane` for Wordle. Board games also have **buttons**
- Two-player games open a lobby with **Join & Play** / **Play vs Bot** buttons; `sttt @friend` starts instantly. Natural phrases work too: `play wordle`
- One game per channel, `sstop` to end it, idle games auto-close after 15 minutes
- `sgame ...` still replies with a short "how to" so old habits are not confusing

### 🆕 New games
- Tic Tac Toe (button board, minimax bot), Connect 4 (image board, bot), Nim, Rock Paper Scissors (secret picks, best of 3)
- Guess the Number (everyone guesses, hot/cold hints), Hangman (gallows image), Wordle (tile image), Word Scramble, Riddles
- Trivia (Open Trivia DB, button answers), Guess the Flag (FlagCDN), Who's That Pokémon (PokéAPI silhouettes)
- XP, levels, `sprofile` image card and `sboard` leaderboard (stored in `.speedy/scores.json`)

### 🧮 Maths Lab
- `smath` menu with 14 topics: arithmetic, fractions & percentages, algebra, quadratics, surds, indices, logarithms, trigonometry, geometry, sequences, calculus, statistics & probability, number theory, vectors & matrices
- Three difficulty levels, picture question cards with triangle diagrams, hint/skip buttons
- Safe, forgiving answer parser (`3√2`, `sqrt(3)/2`, `5π/6`, `3/4`, `x^2+5x+6`, `x=1, y=2`) — no `eval`
- `scalc` calculator and `sfactor` prime factorisation

### 🎉 Fun & media
- 30 anime reaction GIF commands with a "back" button (`shug @friend`, `spat`, `sbonk`, ...)
- `sdog`, `sfox`, `sduck`, `sreddit`, `snasa`, `sgif`, `sfact`, `sadvice`, `szen`, `sdadjoke`, `spokemon`
- `sflip`, `sroll`, `s8ball`, `schoose`, `swyr` (live voting), `struth`, `sdare`, `sping`

### ❓ Help
- `shelp` is now categorised with a dropdown (`shelp games`, `shelp math`, `shelp fun`, `shelp gifs`)

### 🔧 Under the hood
- `bot.py` split into the `speedy/` package (cogs, games, images, maths engine), `commands.Bot` with case-insensitive prefix-less commands
- Pillow added to requirements (images); pytest suite added (`requirements-dev.txt`)
- Existing classic commands and all 85 sticker commands behave as before

---

## Version 2.1.5 - Multiplayer Games (June 5, 2026)

### 🎮 New Feature: ID-Based Game Lobbies
- Added multiplayer game lobbies with per-game IDs so more than one game can run at once
- Players join before the host starts the match, which prevents non-participants from interfering
- Only joined players can make moves once a game is active

### ✨ Supported Games
- **`tictactoe`** - 2-player board game
- **`connect4`** - 2-player connect-four
- **`nim`** - 2-player stone-taking game
- **`guessnumber`** - 1-6 player number guessing game

### 🧾 Command Additions
- **`sgames`** - Game overview and active lobbies
- **`sgame create <game>`** - Create a new game lobby
- **`sgame join <id>`** - Join a lobby before it starts
- **`sgame start <id>`** - Start a lobby as host
- **`sgame move <id> <move>`** - Make a move in the active game
- **`sgame status <id>`** - Show live game state
- **`sgame leave <id>`** - Leave or forfeit a game
- **`sgame cancel <id>`** - Cancel a lobby or game as host

### 📝 Documentation Updates
- Updated README with the new multiplayer workflow
- Added the game system to `shelp` output

---

## Version 2.1.4 - Joke Expansion (June 5, 2026)

### ✨ Content Update
- Expanded the `knock knock` library from 25 jokes to 121 jokes
- Added a large new batch of classic and pun-based knock-knock jokes to `data/jokes.json`
- Kept the existing file format so the command continues working without code changes

### 📊 Updated Totals
- **Knock-knock jokes:** 121
- **Static responses:** 433+

### 📝 Documentation Updates
- Updated README joke counts and overall response totals
- Updated project structure docs to reflect the larger joke dataset

---

## Version 2.1.3 - Sticker Expansion (June 5, 2026)

### ✨ New Features
- Added `shelp` command to show all core, API, and sticker commands in Discord
- Expanded sticker library from 12 categories to 85 commands
- Added 75 new sticker command shortcuts using the requested `s...` naming pattern

### 🎨 Sticker Additions
- Added new reactions like `sgoodnight`, `spardon`, `ssorry`, `sthankyou`, `syass`, `sgoodjob`, `sready`, and many more
- Merged repeated reaction intents cleanly where useful, such as `shi`
- Kept sticker discovery dynamic so `shelp` always reflects `data/stickers.json`

### 📊 Content Totals
- **Sticker commands:** 85
- **Sticker GIF URLs:** 195
- **Static responses:** 337+

### 📝 Documentation Updates
- Updated README command list and content totals
- Documented the new `shelp` helper command
- Corrected GIF troubleshooting guidance to reference Giphy CDN URLs

---

## Version 2.1.2 - GIF URL Migration (June 1, 2026)

### 🔥 Critical Fix: All GIF URLs Replaced
- **Fixed broken GIF URLs:** All Tenor URLs returning 404 errors
- **Migrated to Giphy CDN:** All 150 GIFs now use stable Giphy URLs
- **Format change:** `media1.tenor.com/m/...` → `media.giphy.com/media/.../giphy.gif`
- **Verified working:** All URLs tested and confirmed working in Discord

### 📊 URLs Replaced
- **Meme GIFs:** 30 URLs migrated to Giphy
- **Sticker GIFs:** 120 URLs migrated to Giphy (12 categories × 10)
- **Total:** 150 broken URLs replaced with working ones

### 🎯 Why This Happened
Tenor changed their URL structure, making old `media1.tenor.com/m/` URLs return 404 errors. Giphy provides stable, long-lasting CDN URLs that work reliably in Discord embeds.

### ✅ Benefits
- **Reliable:** Giphy CDN has stable URLs
- **Fast:** High-performance content delivery
- **Compatible:** Works perfectly with Discord embeds
- **No API needed:** Direct CDN URLs require no authentication

### 📝 Documentation Updated
- Updated README with Giphy URL format
- Added warning about deprecated Tenor URLs
- Updated GIF finding instructions to use Giphy

---

## Version 2.1.1 - Bug Fixes (June 1, 2026)

### 🐛 Critical Bug Fixes
- **Fixed multiple response issue:** Commands now use `if` with `return` instead of `elif` chain
- **Fixed "happy birthday" trigger:** Changed from `'happy birthday' in content` to exact match `content == 'happy birthday'`
  - Previously triggered on any message containing those words
  - Now only triggers on exact command
- **Added input sanitization:** Commands now use `.strip()` to remove extra whitespace
- **Immediate return after execution:** Each command returns after sending response to prevent fall-through

### 🔧 Improvements
- **Added `start-safe.sh`** - Prevents multiple bot instances from running simultaneously
- **Added `stop.sh`** - Safely stops all bot instances
- **Process checking:** Bot checks if already running before starting
- **Better error messages:** Clear feedback if bot is already running
- **Made scripts executable:** Helper scripts have proper permissions

### 📝 Documentation Updates
- Added troubleshooting section for multiple responses issue
- Documented helper scripts (start-safe.sh, stop.sh)
- Clarified command matching behavior (exact match required)
- Added process management instructions

### 🎯 Why This Matters
Multiple responses were caused by:
1. Multiple bot instances running simultaneously
2. Command handler using `elif` without early returns
3. "happy birthday" using substring match instead of exact match

All issues now resolved! ✅

---

## Version 2.1 - API Integration (June 1, 2026)

### 🌐 Major Feature: Live API Integration
- **Integrated 5 free APIs** for dynamic, always-fresh content
- No API keys required - all services are free and open

### ✨ New Commands

#### 🐱 Cat Commands
- **`scat`** - Get random cat pictures from TheCatAPI
  - Primary source: TheCatAPI (https://api.thecatapi.com/)
  - Fallback: CATAAS (https://cataas.com/)
  - Beautiful high-quality cat photos every time

- **`catfact`** - Learn interesting cat facts
  - Source: MeowFacts API (https://meowfacts.herokuapp.com/)
  - Educational and fun facts about cats

#### 😄 Joke Commands
- **`sjoke`** - Get random jokes from Official Joke API
  - Source: https://official-joke-api.appspot.com/
  - Family-friendly jokes with setup and punchline

- **`schuck`** - Get Chuck Norris jokes
  - Source: https://api.chucknorris.io/
  - Hilarious Chuck Norris facts

#### ✨ Other Commands
- **`semoji`** - Get random emojis with information
  - Source: EmojiHub (https://emojihub.yurace.pro/)
  - Displays emoji character, name, and category

### 🔧 Technical Improvements
- Added **aiohttp** for async API calls
- Non-blocking API requests for fast response times
- Error handling with graceful fallbacks if APIs are down
- SSL certificate compatibility maintained
- Professional embed formatting for API responses
- Each API command includes attribution in footer

### 📦 Dependencies Updated
- Added `aiohttp>=3.9.0` for async HTTP requests
- Added `requests>=2.31.0` for HTTP support

### 🎨 Content Summary
- **Static Content:** 262 pieces (quotes, greetings, jokes, GIFs)
- **Dynamic API Content:** Unlimited (fresh content every time!)
- **Total Commands:** 18+ commands (13 static + 5 API-powered)

---

## Version 2.0 - JSON Data Structure (June 1, 2026)

### 🎉 Major Changes
- **Migrated all content to JSON files** - No more hardcoded lists in Python!
- All content now lives in the `data/` folder for easy editing

### ✨ Content Expansion
- **Speed Quotes**: 10 → 40 quotes (+300% increase)
- **Cat Greetings**: 10 → 35 greetings (+250% increase)
- **Knock-Knock Jokes**: 8 → 25 jokes (+213% increase)
- **Birthday Messages**: 4 → 12 messages (+200% increase)
- **Meme GIFs**: 6 → 30 GIFs (+400% increase)
- **Sticker GIFs**: 24 → 120 GIFs (+400% increase)

### 🔧 Technical Improvements
- Added JSON loading system with error handling
- Fixed broken GIF URLs (replaced placeholder URLs with working Tenor links)
- Added data validation on startup
- Improved logging with content statistics
- Added fallback messages if JSON files are missing
- Better error messages for debugging

### 📁 New File Structure
```
data/
├── quotes.json     - 40 speed quotes
├── greetings.json  - 35 cat greetings
├── jokes.json      - 25 knock-knock jokes
├── birthday.json   - 12 birthday messages
├── memes.json      - 30 meme GIF URLs
└── stickers.json   - 120 sticker GIFs (12 categories)
```

### 🎨 Customization Made Easy
- Edit JSON files to add/remove/modify content
- No Python coding required for content changes
- Test GIF URLs in browser before adding
- Use proper Tenor URL format for reliable GIFs

### 🐛 Bug Fixes
- Fixed broken GIF URLs showing progress bars
- All GIFs now use valid Tenor CDN links
- Improved SSL certificate handling

---

## Version 1.0 - Initial Release

### Features
- Basic Discord bot with message-based commands
- Speed quotes, cat greetings, knock-knock jokes
- Birthday wishes (double response feature)
- Meme GIFs and reaction stickers
- SSL certificate configuration for macOS
- Environment variable support for bot token

### Content
- 10 speed quotes
- 10 cat greetings
- 8 knock-knock jokes
- 4 birthday messages
- 6 meme GIFs
- 12 sticker commands (2 GIFs each)
