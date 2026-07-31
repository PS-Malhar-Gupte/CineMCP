"""
TMDb-backed release tools for CineMCP.

This module provides MCP tools that query the TMDb API for current and upcoming
movie releases. Each tool is registered against the shared FastMCP
instance imported from server.mcp_instance.

Tools:
- now_playing_india: Get movies currently playing in Indian theaters
- upcoming_releases_india: Get movies about to release in Indian theaters
- upcoming_releases_global: Get upcoming movies worldwide (no region filter)
- recent_releases_global: Get recently released movies worldwide (last 3 months)
- recent_releases_india: Get recently released movies in India (last 3 months)
"""

from server.mcp_instance import mcp
from server.http_utils import tmdb_get, TmdbKeyMissing


@mcp.tool()
def now_playing_india(page: int = 1) -> dict:
    """
    Get movies currently playing in Indian theaters.
    
    This tool queries the TMDb API's now-playing endpoint filtered to the
    India region (IN) to retrieve movies that are currently in theatrical
    release. Results are paginated, with each page containing up to 20 movies.
    
    Args:
        page: Page number for paginated results (default: 1)
    
    Returns:
        dict: On success, returns {"results": [{"title": str, "release_date": str,
              "overview": str}, ...]}.
              On zero results, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.
    
    Example:
        >>> now_playing_india(page=1)
        {"results": [
            {"title": "Movie Name", "release_date": "2024-01-15", 
             "overview": "A brief description of the movie..."},
            ...
        ]}
    
    Note:
        This tool returns only movies currently in theaters in India.
        For upcoming releases, use upcoming_releases_india() instead.
    """
    try:
        # Build TMDb now-playing parameters with India region filter
        params = {
            "region": "IN",
            "page": page
        }
        
        # Make the request to TMDb's now-playing endpoint
        response = tmdb_get("/movie/now_playing", params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the results array
        raw_results = response.get("results", [])
        
        if not raw_results:
            # No movies currently playing in India
            return {
                "results": [],
                "summary": "No movies currently playing in Indian theaters"
            }
        
        # Transform TMDb format into our standard format
        # Only include title, release_date, and overview per requirements
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", "")
            })
        
        return {"results": results}
    
    except TmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in now_playing_india: {str(e)}"}


@mcp.tool()
def upcoming_releases_india(page: int = 1) -> dict:
    """
    Get movies about to release in Indian theaters.
    
    This tool queries the TMDb API's upcoming endpoint filtered to the
    India region (IN) to retrieve movies that will be released soon in
    Indian theaters. Results are paginated, with each page containing up to 20 movies.
    
    Args:
        page: Page number for paginated results (default: 1)
    
    Returns:
        dict: On success, returns {"results": [{"title": str, "release_date": str,
              "overview": str}, ...]}.
              On zero results, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.
    
    Example:
        >>> upcoming_releases_india(page=1)
        {"results": [
            {"title": "Movie Name", "release_date": "2024-03-20", 
             "overview": "A brief description of the upcoming movie..."},
            ...
        ]}
    
    Note:
        This tool returns only upcoming releases in India.
        For movies currently in theaters, use now_playing_india() instead.
    """
    try:
        # Build TMDb upcoming parameters with India region filter
        params = {
            "region": "IN",
            "page": page
        }
        
        # Make the request to TMDb's upcoming endpoint
        response = tmdb_get("/movie/upcoming", params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the results array
        raw_results = response.get("results", [])
        
        if not raw_results:
            # No upcoming movies in India
            return {
                "results": [],
                "summary": "No upcoming movie releases in Indian theaters"
            }
        
        # Transform TMDb format into our standard format
        # Only include title, release_date, and overview per requirements
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", "")
            })
        
        return {"results": results}
    
    except TmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in upcoming_releases_india: {str(e)}"}



@mcp.tool()
def upcoming_releases_global(page: int = 1, year: int | None = None) -> dict:
    """
    Get upcoming movie releases worldwide (no region filter).
    
    This tool queries the TMDb API's upcoming endpoint WITHOUT region filtering
    to retrieve movies that will be released globally. Perfect for finding
    international releases, Hollywood blockbusters, and movies announced for
    future years (2025, 2026, etc.).
    
    Args:
        page: Page number for paginated results (default: 1)
        year: Optional year to filter by (e.g., 2026 for movies releasing in 2026)
    
    Returns:
        dict: On success, returns {"results": [{"title": str, "release_date": str,
              "overview": str, "vote_average": float, "id": int}, ...]}.
              On zero results, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.
    
    Example:
        >>> upcoming_releases_global(page=1, year=2026)
        {"results": [
            {"title": "The Odyssey", "release_date": "2026-07-17", 
             "overview": "A Christopher Nolan epic...", "vote_average": 0.0, "id": 123456},
            ...
        ]}
    
    Note:
        This tool returns GLOBAL upcoming releases (not India-specific).
        For India-specific releases, use upcoming_releases_india() instead.
        For current theatrical releases in India, use now_playing_india().
    """
    try:
        # Build TMDb upcoming parameters WITHOUT region filter
        params = {"page": page}
        
        # If year is specified, use discover endpoint instead for better filtering
        if year:
            # Use discover/movie with release date filters
            params["primary_release_year"] = year
            # Sort by popularity, not release_date.asc - date-only sorting was
            # surfacing arbitrary obscure/low-budget titles sharing the same
            # release date ahead of the notable movie the user actually asked
            # about (observed live: every query returned the same obscure
            # "Clear conscience" result regardless of the actual movie asked for).
            params["sort_by"] = "popularity.desc"
            endpoint = "/discover/movie"
        else:
            endpoint = "/movie/upcoming"
        
        # Make the request to TMDb
        response = tmdb_get(endpoint, params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the results array
        raw_results = response.get("results", [])
        
        if not raw_results:
            summary = "No upcoming movie releases found"
            if year:
                summary = f"No upcoming movie releases found for {year}"
            return {
                "results": [],
                "summary": summary
            }
        
        # Transform TMDb format into our standard format
        # Include additional fields for better context
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", ""),
                "vote_average": item.get("vote_average", 0.0),
                "id": item.get("id", 0)
            })
        
        return {"results": results}
    
    except TmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in upcoming_releases_global: {str(e)}"}



@mcp.tool()
def recent_releases_global(page: int = 1, days: int = 90) -> dict:
    """
    Get recently released movies worldwide (default: last 90 days).
    
    This tool queries the TMDb API's discover endpoint to find movies that
    were released in the last X days globally. Perfect for finding movies
    that just came out in theaters (2 weeks ago, 1 month ago, etc.).
    
    Args:
        page: Page number for paginated results (default: 1)
        days: Number of days to look back (default: 90 = ~3 months)
    
    Returns:
        dict: On success, returns {"results": [{"title": str, "release_date": str,
              "overview": str, "vote_average": float, "id": int}, ...]}.
              On zero results, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.
    
    Example:
        >>> recent_releases_global(page=1, days=30)
        {"results": [
            {"title": "The Odyssey", "release_date": "2025-01-15", 
             "overview": "A Christopher Nolan epic...", "vote_average": 8.5, "id": 123456},
            ...
        ]}
    
    Note:
        This tool returns GLOBAL recent releases (movies that came out recently).
        For upcoming releases, use upcoming_releases_global().
        For current Indian theaters, use now_playing_india().
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate date range (last X days)
        today = datetime.now()
        start_date = today - timedelta(days=days)
        
        # Format dates for TMDb API (YYYY-MM-DD)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = today.strftime("%Y-%m-%d")
        
        # Build TMDb discover parameters
        params = {
            "page": page,
            "primary_release_date.gte": start_date_str,
            "primary_release_date.lte": end_date_str,
            # Sort by popularity within the date window, not raw date - pure
            # date sorting surfaced obscure/low-budget titles ahead of the
            # movie the user actually meant, same issue as upcoming_releases_global.
            "sort_by": "popularity.desc"
        }
        
        # Make the request to TMDb discover endpoint
        response = tmdb_get("/discover/movie", params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the results array
        raw_results = response.get("results", [])
        
        if not raw_results:
            return {
                "results": [],
                "summary": f"No movies released in the last {days} days"
            }
        
        # Transform TMDb format into our standard format
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", ""),
                "vote_average": item.get("vote_average", 0.0),
                "id": item.get("id", 0)
            })
        
        return {"results": results}
    
    except TmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in recent_releases_global: {str(e)}"}


@mcp.tool()
def recent_releases_india(page: int = 1, days: int = 90) -> dict:
    """
    Get recently released movies in India (default: last 90 days).

    This tool queries TMDb's discover endpoint with an India region filter
    combined with a release-date window, to find movies released in the
    last X days specifically in India. This exists as a separate tool from
    now_playing_india() because TMDb's curated /movie/now_playing endpoint
    has an unreliable region filter - it is Hollywood/US-centric by default
    and its India region filtering does not reliably surface India-specific
    (including regional/Bollywood) titles. Using /discover/movie with an
    explicit region + date-range filter is the more reliable approach.

    Args:
        page: Page number for paginated results (default: 1)
        days: Number of days to look back (default: 90 = ~3 months)

    Returns:
        dict: On success, returns {"results": [{"title": str, "release_date": str,
              "overview": str, "vote_average": float, "id": int}, ...]}.
              On zero results, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.

    Example:
        >>> recent_releases_india(page=1, days=30)
        {"results": [
            {"title": "Some Recent Film", "release_date": "2026-07-10",
             "overview": "...", "vote_average": 7.2, "id": 654321},
            ...
        ]}

    Note:
        This tool returns INDIA-SPECIFIC recent releases.
        For movies currently still in theaters, use now_playing_india().
        For global (non-India) recent releases, use recent_releases_global().
    """
    try:
        from datetime import datetime, timedelta

        # Calculate date range (last X days)
        today = datetime.now()
        start_date = today - timedelta(days=days)

        # Format dates for TMDb API (YYYY-MM-DD)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = today.strftime("%Y-%m-%d")

        # Build TMDb discover parameters with an explicit India region filter,
        # sorted by popularity within the window (see recent_releases_global
        # for why pure date-sorting was rejected - same reasoning applies here)
        params = {
            "page": page,
            "region": "IN",
            "primary_release_date.gte": start_date_str,
            "primary_release_date.lte": end_date_str,
            "sort_by": "popularity.desc"
        }

        # Make the request to TMDb discover endpoint
        response = tmdb_get("/discover/movie", params)

        # Check for errors
        if "error" in response:
            return response

        # Extract the results array
        raw_results = response.get("results", [])

        if not raw_results:
            return {
                "results": [],
                "summary": f"No movies released in India in the last {days} days"
            }

        # Transform TMDb format into our standard format
        results = []
        for item in raw_results:
            results.append({
                "title": item.get("title", ""),
                "release_date": item.get("release_date", ""),
                "overview": item.get("overview", ""),
                "vote_average": item.get("vote_average", 0.0),
                "id": item.get("id", 0)
            })

        return {"results": results}

    except TmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in recent_releases_india: {str(e)}"}