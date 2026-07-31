"""
OMDb-backed movie tools for CineMCP.

This module provides MCP tools that query the OMDb API for movie search,
details, and ratings. Each tool is registered against the shared FastMCP
instance imported from server.mcp_instance.

Tools:
- search_movie: Search for movies by title, optionally filtered by year
- movie_details: Get full details (plot, cast, crew, etc.) for a specific IMDb ID
- movie_ratings: Get ratings breakdown for a specific IMDb ID
"""

from server.mcp_instance import mcp
from server.http_utils import omdb_get, OmdbKeyMissing


@mcp.tool()
def search_movie(title: str, year: str = "") -> dict:
    """
    Search for movies by title, optionally filtered by year.
    
    This tool queries the OMDb API's search endpoint to find movies matching
    the given title. Returns a list of candidates with their IMDb IDs, which
    can be used with movie_details() or movie_ratings() for more information.
    
    Args:
        title: The movie title to search for (e.g., "Inception")
        year: Optional year to filter results (e.g., "2010")
    
    Returns:
        dict: On success, returns {"results": [{"imdb_id": str, "title": str, 
              "year": str, "type": str}, ...]}.
              On zero matches, returns {"results": [], "summary": str}.
              On error, returns {"error": str}.
    
    Example:
        >>> search_movie("Inception", "2010")
        {"results": [{"imdb_id": "tt1375666", "title": "Inception", 
                      "year": "2010", "type": "movie"}]}
    
    Note:
        If you have a plain movie title but need detailed information,
        call this tool first to get the IMDb ID, then pass that ID to
        movie_details() or movie_ratings().
    """
    try:
        # Build OMDb search parameters
        params = {"s": title}
        if year:
            params["y"] = year
        
        # Make the request
        response = omdb_get(params)
        
        # Check for errors
        # Special case: "Movie not found!" means zero results, not a real error
        if "error" in response:
            error_msg = response["error"]
            if "not found" in error_msg.lower():
                # Treat "not found" as zero results
                summary = f"No movies found matching title '{title}'"
                if year:
                    summary += f" from year {year}"
                return {
                    "results": [],
                    "summary": summary
                }
            # Other errors should be returned as-is
            return response
        
        # Check if search returned results
        search_results = response.get("Search", [])
        
        if not search_results:
            # No matches found
            summary = f"No movies found matching title '{title}'"
            if year:
                summary += f" from year {year}"
            return {
                "results": [],
                "summary": summary
            }
        
        # Transform OMDb's Search format into our standard format
        results = []
        for item in search_results:
            results.append({
                "imdb_id": item.get("imdbID", ""),
                "title": item.get("Title", ""),
                "year": item.get("Year", ""),
                "type": item.get("Type", "")
            })
        
        return {"results": results}
    
    except OmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in search_movie: {str(e)}"}


@mcp.tool()
def movie_details(imdb_id: str) -> dict:
    """
    Get full details (plot, cast, crew, etc.) for a specific IMDb ID.
    
    This tool queries the OMDb API to retrieve comprehensive information about
    a movie including its plot, director, writer, actors, genre, runtime, country,
    language, and awards. This tool does NOT return ratings information - use
    movie_ratings() for that.
    
    IMPORTANT: This tool requires an IMDb ID (e.g., "tt1375666"), NOT a plain
    movie title. If you only have a movie title, you MUST first call search_movie()
    to resolve the title to an IMDb ID, then pass that ID to this tool.
    
    Args:
        imdb_id: The IMDb ID of the movie (e.g., "tt1375666" for Inception)
    
    Returns:
        dict: On success, returns {
            "title": str,
            "year": str,
            "director": str,
            "writer": str,
            "actors": str,
            "genre": str,
            "runtime": str,
            "country": str,
            "language": str,
            "awards": str,
            "plot": str
        }
        On error (invalid IMDb ID, movie not found, etc.), returns {"error": str}.
    
    Example:
        >>> movie_details("tt1375666")
        {"title": "Inception", "year": "2010", "director": "Christopher Nolan",
         "writer": "Christopher Nolan", "actors": "Leonardo DiCaprio, ...",
         "genre": "Action, Sci-Fi, Thriller", "runtime": "148 min",
         "country": "United States, United Kingdom", "language": "English, Japanese, French",
         "awards": "Won 4 Oscars. 157 wins & 220 nominations total",
         "plot": "A thief who steals corporate secrets..."}
    
    Workflow:
        If you don't have an IMDb ID:
        1. Call search_movie(title="Movie Name") to get candidate IMDb IDs
        2. Choose the appropriate IMDb ID from the search results
        3. Call movie_details(imdb_id="tt...") with that ID
    """
    try:
        # Build OMDb ID lookup parameters
        params = {"i": imdb_id}
        
        # Make the request
        response = omdb_get(params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the details fields (excluding ratings)
        details = {
            "title": response.get("Title", ""),
            "year": response.get("Year", ""),
            "director": response.get("Director", ""),
            "writer": response.get("Writer", ""),
            "actors": response.get("Actors", ""),
            "genre": response.get("Genre", ""),
            "runtime": response.get("Runtime", ""),
            "country": response.get("Country", ""),
            "language": response.get("Language", ""),
            "awards": response.get("Awards", ""),
            "plot": response.get("Plot", "")
        }
        
        return details
    
    except OmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in movie_details: {str(e)}"}


@mcp.tool()
def movie_ratings(imdb_id: str) -> dict:
    """
    Get ratings breakdown for a specific IMDb ID.
    
    This tool queries the OMDb API to retrieve ratings information about a movie,
    including IMDb rating, IMDb vote count, Metascore, and ratings from various
    sources (Rotten Tomatoes, Metacritic, etc.). This tool does NOT return plot,
    cast, or crew information - use movie_details() for that.
    
    IMPORTANT: This tool requires an IMDb ID (e.g., "tt1375666"), NOT a plain
    movie title. If you only have a movie title, you MUST first call search_movie()
    to resolve the title to an IMDb ID, then pass that ID to this tool.
    
    Args:
        imdb_id: The IMDb ID of the movie (e.g., "tt1375666" for Inception)
    
    Returns:
        dict: On success, returns {
            "imdb_rating": str,
            "imdb_votes": str,
            "metascore": str,
            "ratings": [{"source": str, "value": str}, ...]
        }
        On error (invalid IMDb ID, movie not found, etc.), returns {"error": str}.
    
    Example:
        >>> movie_ratings("tt1375666")
        {"imdb_rating": "8.8", "imdb_votes": "2,500,000",
         "metascore": "74",
         "ratings": [
             {"source": "Internet Movie Database", "value": "8.8/10"},
             {"source": "Rotten Tomatoes", "value": "87%"},
             {"source": "Metacritic", "value": "74/100"}
         ]}
    
    Workflow:
        If you don't have an IMDb ID:
        1. Call search_movie(title="Movie Name") to get candidate IMDb IDs
        2. Choose the appropriate IMDb ID from the search results
        3. Call movie_ratings(imdb_id="tt...") with that ID
    """
    try:
        # Build OMDb ID lookup parameters
        params = {"i": imdb_id}
        
        # Make the request
        response = omdb_get(params)
        
        # Check for errors
        if "error" in response:
            return response
        
        # Extract the ratings-related fields only
        ratings = {
            "imdb_rating": response.get("imdbRating", "N/A"),
            "imdb_votes": response.get("imdbVotes", "N/A"),
            "metascore": response.get("Metascore", "N/A"),
            "ratings": response.get("Ratings", [])
        }
        
        return ratings
    
    except OmdbKeyMissing as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error in movie_ratings: {str(e)}"}
