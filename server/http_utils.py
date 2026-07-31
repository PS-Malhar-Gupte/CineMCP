"""
HTTP client utilities for external movie APIs (OMDb and TMDb).

Each data source has its own request function that handles:
- API key attachment from environment variables
- Failure normalization into a consistent {"error": "..."} shape
- Network timeout handling
"""

import os
import requests


# Custom exceptions for missing API keys
class OmdbKeyMissing(Exception):
    """Raised when OMDB_API_KEY environment variable is not set."""
    pass


class TmdbKeyMissing(Exception):
    """Raised when TMDB_API_KEY environment variable is not set."""
    pass


# OMDb API base URL
OMDB_BASE_URL = "http://www.omdbapi.com/"

# TMDb API base URL
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Request timeout in seconds
REQUEST_TIMEOUT = 15


def omdb_get(params: dict) -> dict:
    """
    Make a GET request to OMDb API with automatic API key attachment.
    
    OMDb has an unusual failure signaling convention: it returns HTTP 200
    with {"Response": "False", "Error": "..."} instead of using proper HTTP
    error codes. This function normalizes that into a plain {"error": "..."}
    dict for consistent error handling throughout the codebase.
    
    Args:
        params: Query parameters for the OMDb API (e.g., {"s": "Inception"})
    
    Returns:
        dict: The OMDb response data, or {"error": "..."} on failure
    
    Raises:
        OmdbKeyMissing: If OMDB_API_KEY environment variable is not set
    
    Example:
        >>> omdb_get({"s": "Inception"})
        {"Search": [...], "totalResults": "10", "Response": "True"}
        
        >>> omdb_get({"i": "invalid123"})
        {"error": "Incorrect IMDb ID."}
    """
    # Check for API key in environment
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        raise OmdbKeyMissing(
            "OMDB_API_KEY environment variable is not set. "
            "Get a free key at https://www.omdbapi.com/apikey.aspx"
        )
    
    # Attach API key to request parameters
    request_params = {**params, "apikey": api_key}
    
    try:
        # Make the request with timeout
        response = requests.get(
            OMDB_BASE_URL,
            params=request_params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Normalize OMDb's unusual error format
        # OMDb returns HTTP 200 with {"Response": "False", "Error": "..."}
        if data.get("Response") == "False":
            error_message = data.get("Error", "Unknown error from OMDb")
            return {"error": error_message}
        
        return data
        
    except requests.exceptions.Timeout:
        return {"error": f"OMDb API request timed out after {REQUEST_TIMEOUT}s"}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error contacting OMDb: {str(e)}"}
    
    except ValueError as e:
        # JSON parsing failed
        return {"error": f"Invalid JSON response from OMDb: {str(e)}"}


def tmdb_get(path: str, params: dict) -> dict:
    """
    Make a GET request to TMDb API with automatic API key attachment.
    
    TMDb uses standard HTTP status codes for error signaling (unlike OMDb).
    4xx/5xx responses are normalized into {"error": "..."} for consistent
    error handling throughout the codebase.
    
    Args:
        path: API endpoint path (e.g., "/movie/now_playing")
        params: Query parameters for the TMDb API (e.g., {"region": "IN"})
    
    Returns:
        dict: The TMDb response data, or {"error": "..."} on failure
    
    Raises:
        TmdbKeyMissing: If TMDB_API_KEY environment variable is not set
    
    Example:
        >>> tmdb_get("/movie/now_playing", {"region": "IN"})
        {"results": [...], "page": 1, "total_pages": 5}
        
        >>> tmdb_get("/movie/invalid", {})
        {"error": "HTTP 404: The resource you requested could not be found."}
    """
    # Check for API key in environment
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise TmdbKeyMissing(
            "TMDB_API_KEY environment variable is not set. "
            "Get a free key at https://www.themoviedb.org/settings/api"
        )
    
    # Attach API key to request parameters
    request_params = {**params, "api_key": api_key}
    
    # Build full URL
    url = f"{TMDB_BASE_URL}{path}"
    
    try:
        # Make the request with timeout
        response = requests.get(
            url,
            params=request_params,
            timeout=REQUEST_TIMEOUT
        )
        
        # TMDb uses standard HTTP status codes for errors
        # Raise an exception for 4xx/5xx responses
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        return data
        
    except requests.exceptions.HTTPError as e:
        # HTTP 4xx/5xx error
        status_code = e.response.status_code if e.response else "unknown"
        try:
            # TMDb often includes an error message in the response body
            error_data = e.response.json()
            error_message = error_data.get("status_message", str(e))
        except:
            error_message = str(e)
        return {"error": f"HTTP {status_code}: {error_message}"}
    
    except requests.exceptions.Timeout:
        return {"error": f"TMDb API request timed out after {REQUEST_TIMEOUT}s"}
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error contacting TMDb: {str(e)}"}
    
    except ValueError as e:
        # JSON parsing failed
        return {"error": f"Invalid JSON response from TMDb: {str(e)}"}
