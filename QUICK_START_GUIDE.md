# Quick Start Guide - Testing Your Updated Agent

## What's New?

Your agent can now find movies from **any time period**:
- ✅ **Recently released** (last 2 weeks, last month) - NEW!
- ✅ **Currently in theaters** (India)
- ✅ **Coming soon** (2025, 2026+)
- ✅ **Any movie ever** (via IMDb)

## How to Test

### Step 1: Restart Your Agent

**CLI Mode:**
```bash
cd c:\Users\MalharGupte\Downloads\CineMCP
python -m agent.main
```

**Web Mode:**

Terminal 1 - Backend:
```bash
cd c:\Users\MalharGupte\Downloads\CineMCP\web\backend
uvicorn main:app --reload
```

Terminal 2 - Frontend:
```bash
cd c:\Users\MalharGupte\Downloads\CineMCP\web\frontend
npm run dev
```

Then open: http://localhost:5173

### Step 2: Test These Queries

#### Test Recently Released Movies
```
> Tell me about The Odyssey released 2 weeks ago
> What's the Backrooms movie that just came out?
> Show me movies from last month
```

**Expected:** Agent calls `recent_releases_global(days=30)` and finds the movie

#### Test Future Releases
```
> Tell me about The Odyssey coming in 2026
> What movies are releasing in 2026?
> Christopher Nolan upcoming films
```

**Expected:** Agent calls `upcoming_releases_global(year=2026)`

#### Test Current Releases
```
> What's playing in India?
> Current movies in theaters
```

**Expected:** Agent calls `now_playing_india()`

#### Test Classic Movies
```
> Tell me about Inception
> What's The Shawshank Redemption about?
```

**Expected:** Agent calls `search_movie()` then `movie_details()`

## Tools Available

| Tool | When to Use | Example Query |
|------|-------------|---------------|
| `recent_releases_global` | "Released X ago" | "Movie from 2 weeks ago" |
| `upcoming_releases_global` | "Coming in 2026" | "2026 releases" |
| `now_playing_india` | "What's playing in India" | "Current India theaters" |
| `upcoming_releases_india` | "Coming soon in India" | "Upcoming India releases" |
| `search_movie` | Specific movie + details | "Tell me about Inception" |
| `movie_details` | Full info (cast, plot, etc) | Called after search_movie |
| `movie_ratings` | Ratings only | Called after search_movie |

## Troubleshooting

### "I couldn't find..."

**Check:**
1. Is the MCP server running? (Should see `[DEBUG] Starting MCP server...` in logs)
2. Are API keys set in `.env`? (TMDB_API_KEY, OMDB_API_KEY, OPENAI_API_KEY)
3. Is the agent calling tools? (Should see tool calls in logs)

**Debug:**
```bash
# Test tool directly
python test_recent_tool.py

# Check .env
type .env
```

### Agent not calling tools

**Symptom:** Agent says "I'll check..." but doesn't actually call tools

**Fix:** System prompt issue - already fixed in latest version

**Verify:**
```bash
# Check system prompt has recent_releases_global
type agent\config.py | findstr "recent_releases"
```

### API rate limits

**TMDb Free Tier:**
- 40 requests / 10 seconds
- 1,000 requests / day

**If you hit limits:**
- Wait 10 seconds and try again
- Reduce number of queries
- Consider caching (future enhancement)

## What Changed?

### New Tool: `recent_releases_global`
- **File:** `server/release_tools.py`
- **Function:** Find movies released in last X days
- **Usage:** `recent_releases_global(page=1, days=90)`

### Updated System Prompt
- **File:** `agent/config.py`
- **Change:** Added instructions for "recently released" queries
- **Now includes:** 7 tools (was 6)

### Test Files
- `test_recent_tool.py` - Test recent releases tool
- `test_recent_odyssey.py` - Search for The Odyssey
- `find_odyssey.py` - Find in 2026 releases

## Example Conversation

```
User: Tell me about The Odyssey released 2 weeks ago

Agent: [Thinking...]
       Calling tool: recent_releases_global(page=1, days=30)
       [Searching results for "Odyssey"...]
       Found it!

Agent: The Odyssey was released on January 15, 2025. 
       It's an epic adventure film directed by Christopher Nolan...
       [Full plot summary from TMDb]
       Rating: 8.5/10
```

## Documentation Files

- **PROJECT_HANDBOOK.md** - Complete project documentation
- **WHATS_NEW.md** - 2026 movie support update
- **RECENT_RELEASES_FIX.md** - This recent release fix
- **QUICK_START_GUIDE.md** - This file
- **README.md** - Basic setup instructions

## Need Help?

1. **Check logs** - Agent prints debug info to console
2. **Test tools directly** - Run `test_recent_tool.py`
3. **Verify .env** - Make sure all API keys are set
4. **Read docs** - See PROJECT_HANDBOOK.md for full details

---

**Status:** ✅ Ready to use!

**Last Updated:** January 27, 2025

**Your agent now has complete time coverage - enjoy!** 🎬🚀
