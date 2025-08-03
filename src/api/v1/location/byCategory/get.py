from fastapi import HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from src.datamodel.database.domain.DigitalSignage import Location
from src.datamodel.datavalidation.apiconfig import ApiConfig


logger = logging.getLogger(__name__)


def api_config():
    config = {
        "path": "",
        "status_code": 200,
        "tags": ["Location"],
        "summary": "Search Locations",
        "response_model": dict,
        "description": "Search locations by name, category, or description with advanced filtering options including floor-based filtering.",
        "response_description": "Search results",
        "deprecated": False,
    }
    return ApiConfig(**config)


class LocationSearchResponse(BaseModel):
    location_id: str
    name: str
    category: str
    floor_id: str
    shape: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    color: str
    text_color: str
    is_published: bool
    description: Optional[str] = None
    status: str
    datetime: float
    relevance_score: Optional[float] = None

    class Config:
        allow_population_by_field_name = True


class SearchResultsResponse(BaseModel):
    query: str
    total_results: int
    results: List[LocationSearchResponse]
    search_filters: dict
    floors_found: List[str]

    class Config:
        allow_population_by_field_name = True


async def main(
    q: str = Query(..., description="Search query (searches in name, category, and description)"),
    status_filter: Optional[str] = Query("active", description="Filter by status (active, inactive, deleted, all)"),
    category: Optional[str] = Query(None, description="Filter by specific category"),
    floor_id: Optional[str] = Query(None, description="Filter by specific floor ID"),
    shape: Optional[str] = Query(None, description="Filter by shape type (circle, rectangle)"),
    limit: Optional[int] = Query(20, description="Limit number of results"),
    skip: Optional[int] = Query(0, description="Skip number of results for pagination"),
    exact_match: Optional[bool] = Query(False, description="Use exact match instead of partial match"),
    sort_by: Optional[str] = Query("relevance", description="Sort by field (relevance, name, category, datetime, floor_id)")
):
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters long"
            )

        # Build search query
        search_pattern = q.strip()
        if exact_match:
            # Exact match search
            search_conditions = [
                {"name": {"$regex": f"^{search_pattern}$", "$options": "i"}},
                {"category": {"$regex": f"^{search_pattern}$", "$options": "i"}},
                {"description": {"$regex": f"^{search_pattern}$", "$options": "i"}}
            ]
        else:
            # Partial match search
            search_conditions = [
                {"name": {"$regex": search_pattern, "$options": "i"}},
                {"category": {"$regex": search_pattern, "$options": "i"}},
                {"description": {"$regex": search_pattern, "$options": "i"}}
            ]

        # Build main query filter
        query_filter = {
            "$or": search_conditions
        }
        
        # Add additional filters
        if status_filter and status_filter != "all":
            query_filter["status"] = status_filter
            
        if category:
            query_filter["category"] = {"$regex": category, "$options": "i"}
            
        if floor_id:
            query_filter["floor_id"] = floor_id
            
        if shape:
            query_filter["shape"] = shape

        # Execute search query
        if sort_by == "relevance":
            # For relevance sorting, we'll use text search if available, otherwise sort by name
            query = Location.find(query_filter).sort("name")
        else:
            sort_direction = 1 if sort_by != "datetime" else -1  # Newest first for datetime
            query = Location.find(query_filter).sort([(sort_by, sort_direction)])
        
        if skip:
            query = query.skip(skip)
        if limit:
            query = query.limit(limit)
            
        locations = await query.to_list()
        
        # Calculate relevance scores and prepare response
        location_list = []
        floors_found = set()
        
        for location in locations:
            # Track floors found in search results
            if location.floor_id:
                floors_found.add(location.floor_id)
            
            # Simple relevance scoring based on where the match occurs
            relevance_score = 0.0
            search_lower = search_pattern.lower()
            
            if location.name and search_lower in location.name.lower():
                if location.name.lower().startswith(search_lower):
                    relevance_score += 3.0  # Higher score for name prefix match
                else:
                    relevance_score += 2.0  # Medium score for name partial match
                    
            if location.category and search_lower in location.category.lower():
                if location.category.lower().startswith(search_lower):
                    relevance_score += 2.0  # Higher score for category prefix match
                else:
                    relevance_score += 1.0  # Lower score for category partial match
                    
            if location.description and search_lower in location.description.lower():
                relevance_score += 0.5  # Lowest score for description match
            
            location_response = LocationSearchResponse(
                location_id=location.location_id,
                name=location.name,
                category=location.category,
                floor_id=location.floor_id,
                shape=location.shape.value,
                x=location.x,
                y=location.y,
                width=location.width,
                height=location.height,
                radius=location.radius,
                logo_url=location.logo_url,
                color=location.color,
                text_color=location.text_color,
                is_published=location.is_published,    
                description=location.description,
                status=location.status,
                datetime=location.datetime,
                relevance_score=relevance_score
            )
            location_list.append(location_response)

        # Sort by relevance if requested
        if sort_by == "relevance":
            location_list.sort(key=lambda x: x.relevance_score, reverse=True)

        # Create comprehensive response
        search_filters = {
            "status": status_filter,
            "category": category,
            "floor_id": floor_id,
            "shape": shape,
            "exact_match": exact_match,
            "sort_by": sort_by
        }

        response = SearchResultsResponse(
            query=search_pattern,
            total_results=len(location_list),
            results=location_list,
            search_filters=search_filters,
            floors_found=list(floors_found)
        )

        logger.info(f"Search completed for query '{search_pattern}': {len(location_list)} results found across {len(floors_found)} floors")

        return {
            "status": "success",
            "message": f"Found {len(location_list)} locations matching '{search_pattern}' across {len(floors_found)} floors",
            "data": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error searching locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search locations: {str(e)}"
        )
