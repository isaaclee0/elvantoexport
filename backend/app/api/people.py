from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from ..elvanto_client import ElvantoClient

router = APIRouter(prefix="/api", tags=["people"])

class BaseRequest(BaseModel):
    api_key: str

class FilterRequest(BaseRequest):
    group_ids: List[str] = []
    service_position_ids: List[str] = []
    excluded_category_ids: List[str] = []
    excluded_group_category_ids: List[str] = []

class GroupsAndServicesRequest(BaseRequest):
    excluded_group_category_ids: List[str] = []

class CategoriesRequest(BaseRequest):
    pass

def _is_adult(person: Dict) -> bool:
    """
    Check if a person should be included as an adult.
    - Include if demographics has 'Adults'
    - Include if no demographics are set (assume adult)
    - Exclude only if explicitly marked as 'Children' (and not also 'Adults')
    """
    demographics = person.get("demographics", {})
    if not demographics or not isinstance(demographics, dict):
        return True
    
    demo_list = demographics.get("demographic", [])
    if isinstance(demo_list, dict):
        demo_list = [demo_list]
    
    if not demo_list:
        return True
    
    demo_names = [d.get("name", "").lower() for d in demo_list]
    
    if "adults" in demo_names:
        return True
    
    if "children" in demo_names:
        return False
    
    return True

def should_include_person(person: Dict, excluded_category_ids: List[str] = None) -> bool:
    """Check if a person should be included based on all criteria"""
    if excluded_category_ids is None:
        excluded_category_ids = []
    
    # Exclude archived people
    archived = person.get("archived", 0)
    if archived == 1 or archived == "1" or str(archived).lower() == "true":
        return False
    
    # Exclude people in excluded categories
    category_id = person.get("category_id", "")
    if category_id in excluded_category_ids:
        return False
    
    # Check demographics - exclude children
    if not _is_adult(person):
        return False
    
    return True

def get_leaders_from_group(group: Dict) -> List[Dict]:
    """Extract only leaders from a group's people list"""
    people_data = group.get("people", {})
    if not people_data:
        return []
    
    persons = people_data.get("person", [])
    if isinstance(persons, dict):
        persons = [persons]
    
    leaders = [p for p in persons if p.get("position", "").lower() == "leader"]
    return leaders

def get_person_positions_from_departments(person: Dict) -> List[Dict]:
    """Extract all volunteer position names from a person's departments"""
    positions = []
    
    depts = person.get("departments", {})
    if not depts or not isinstance(depts, dict):
        return positions
    
    dept_list = depts.get("department", [])
    if isinstance(dept_list, dict):
        dept_list = [dept_list]
    
    for dept in dept_list:
        dept_name = dept.get("name", "Unknown")
        
        sub_depts = dept.get("sub_departments", {})
        if not sub_depts or not isinstance(sub_depts, dict):
            continue
        
        sub_list = sub_depts.get("sub_department", [])
        if isinstance(sub_list, dict):
            sub_list = [sub_list]
        
        for sub in sub_list:
            sub_name = sub.get("name", "")
            
            # Skip if no sub-department name
            if not sub_name:
                continue
            
            positions_data = sub.get("positions", {})
            if not positions_data or not isinstance(positions_data, dict):
                continue
            
            pos_list = positions_data.get("position", [])
            if isinstance(pos_list, dict):
                pos_list = [pos_list]
            
            for pos in pos_list:
                # Use sub-department name as the position name
                # This matches the collapsed format from extract_volunteer_positions_from_people
                display_name = sub_name
                
                positions.append({
                    "id": display_name,
                    "name": display_name,
                    "department": dept_name
                })
    
    return positions

@router.post("/categories")
async def get_categories(request: CategoriesRequest):
    """Get all people categories for exclusion selection"""
    try:
        client = ElvantoClient(api_key=request.api_key)
        categories = client.get_all_categories()
        
        return {
            "categories": [
                {
                    "id": cat.get("id", ""),
                    "name": cat.get("name", "Unknown")
                }
                for cat in categories
            ]
        }
    except Exception as e:
        import traceback
        print(f"Error fetching categories: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/group-categories")
async def get_group_categories(request: CategoriesRequest):
    """Get all group categories extracted from groups, plus a 'no category' option"""
    try:
        client = ElvantoClient(api_key=request.api_key)
        
        # Fetch groups with categories field
        groups = client.get_all_groups_with_categories()
        
        # Extract unique categories from groups
        categories_dict = {}
        groups_without_category = 0
        
        for group in groups:
            categories = group.get("categories")
            if categories:
                # Handle dict structure: {"category": [...]}
                if isinstance(categories, dict):
                    cat_list = categories.get("category", [])
                    if isinstance(cat_list, dict):
                        cat_list = [cat_list]
                elif isinstance(categories, list):
                    cat_list = categories
                elif isinstance(categories, str):
                    # If it's a string, we can't extract id/name, skip
                    continue
                else:
                    cat_list = []
                
                for cat in cat_list:
                    if isinstance(cat, dict):
                        cat_id = cat.get("id")
                        cat_name = cat.get("name")
                        if cat_id and cat_name:
                            categories_dict[cat_id] = cat_name
            else:
                groups_without_category += 1
        
        # Build categories list
        categories_list = [
            {
                "id": cat_id,
                "name": cat_name
            }
            for cat_id, cat_name in sorted(categories_dict.items(), key=lambda x: x[1])
        ]
        
        # Add "no category" option if there are groups without categories
        if groups_without_category > 0:
            categories_list.insert(0, {
                "id": "__no_category__",
                "name": "No Category"
            })
        
        return {
            "categories": categories_list
        }
    except Exception as e:
        import traceback
        print(f"Error fetching group categories: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/groups-and-services")
async def get_groups_and_service_positions(request: GroupsAndServicesRequest):
    """Get combined list of groups and volunteer positions (all groups, no filtering - done client-side)"""
    return await _get_groups_and_service_positions_impl(request.api_key)

def group_has_excluded_category(group: Dict, excluded_category_ids: List[str]) -> bool:
    """Check if a group has any of the excluded categories"""
    if not excluded_category_ids:
        return False
    
    # Handle "__no_category__" special case
    if "__no_category__" in excluded_category_ids:
        categories = group.get("categories")
        if not categories:
            return True  # Group has no category and we're excluding "no category"
        # Check if categories is empty
        if isinstance(categories, dict):
            cat_list = categories.get("category", [])
            if isinstance(cat_list, dict):
                cat_list = [cat_list]
            if not cat_list:
                return True
        elif isinstance(categories, list) and not categories:
            return True
    
    # Check if group has any excluded category
    categories = group.get("categories")
    if not categories:
        return False  # No categories, but we're not excluding "no category" here
    
    # Extract category IDs from group
    if isinstance(categories, dict):
        cat_list = categories.get("category", [])
        if isinstance(cat_list, dict):
            cat_list = [cat_list]
    elif isinstance(categories, list):
        cat_list = categories
    else:
        cat_list = []
    
    for cat in cat_list:
        if isinstance(cat, dict):
            cat_id = cat.get("id")
            if cat_id and cat_id in excluded_category_ids:
                return True
    
    return False

async def _get_groups_and_service_positions_impl(api_key: str):
    """Internal implementation for getting groups and services (no filtering - done client-side)"""
    try:
        client = ElvantoClient(api_key=api_key)
        
        # Get all groups with people AND categories
        try:
            # We need both people (for leaders) and categories (for filtering)
            groups_with_people = client.get_all_groups_with_people()
            groups_with_categories = client.get_all_groups_with_categories()
            
            # Create a lookup for categories by group ID
            categories_by_group_id = {}
            for group in groups_with_categories:
                group_id = group.get("id")
                if group_id:
                    categories_by_group_id[group_id] = group.get("categories")
            
            # Merge categories into groups_with_people
            for group in groups_with_people:
                group_id = group.get("id")
                if group_id in categories_by_group_id:
                    group["categories"] = categories_by_group_id[group_id]
            
            groups = groups_with_people
            print(f"Fetched {len(groups)} groups")
        except Exception as e:
            print(f"Error fetching groups: {str(e)}")
            groups = []
        
        # Get volunteer positions from people's departments
        # No category filtering here - filtering happens when getting people
        positions = {}
        try:
            people = client.get_all_people_with_departments(adults_only=False)
            print(f"Fetched {len(people)} people with departments")
            
            positions = client.extract_volunteer_positions_from_people(people)
            if not isinstance(positions, dict):
                positions = {}
            print(f"Extracted {len(positions)} volunteer positions")
        except Exception as e:
            import traceback
            print(f"Error fetching people/positions: {str(e)}")
            print(traceback.format_exc())
            positions = {}
        
        # Format groups for selection - count only leaders, include category info
        group_list = []
        for group in groups:
            if not group.get("id"):
                continue
            
            # Extract category IDs from group
            category_ids = []
            categories = group.get("categories")
            if categories:
                if isinstance(categories, dict):
                    cat_list = categories.get("category", [])
                    if isinstance(cat_list, dict):
                        cat_list = [cat_list]
                elif isinstance(categories, list):
                    cat_list = categories
                else:
                    cat_list = []
                
                for cat in cat_list:
                    if isinstance(cat, dict):
                        cat_id = cat.get("id")
                        if cat_id:
                            category_ids.append(cat_id)
            
            # If no categories, mark as "__no_category__"
            if not category_ids:
                category_ids = ["__no_category__"]
            
            leaders = get_leaders_from_group(group)
            group_list.append({
                "id": str(group.get("id", "")),
                "name": group.get("name", "Unnamed Group"),
                "type": "group",
                "member_count": len(leaders),
                "category_ids": category_ids  # Include category info for client-side filtering
            })
        
        # Format volunteer positions for selection
        position_list = [
            {
                "id": str(pos_data.get("id", "")),
                "name": pos_data.get("name", "Unknown"),
                "department": pos_data.get("department", ""),
                "type": "service",
                "member_count": len(pos_data.get("volunteers", []))
            }
            for pos_id, pos_data in positions.items()
        ]
        
        combined = group_list + position_list
        return {
            "items": combined,
            "count": len(combined),
            "groups_count": len(group_list),
            "positions_count": len(position_list)
        }
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in get_groups_and_services: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/filter")
async def filter_people(request: FilterRequest):
    """Filter people based on selected groups and volunteer positions"""
    try:
        client = ElvantoClient(api_key=request.api_key)
        excluded_category_ids = request.excluded_category_ids
        excluded_group_category_ids = request.excluded_group_category_ids or []
        
        filtered_people = {}
        
        # Process groups - ONLY include leaders
        if request.group_ids:
            try:
                # Get groups with both people and categories
                groups_with_people = client.get_all_groups_with_people()
                groups_with_categories = client.get_all_groups_with_categories()
                
                # Create a lookup for categories by group ID
                categories_by_group_id = {}
                for group in groups_with_categories:
                    group_id = group.get("id")
                    if group_id:
                        categories_by_group_id[group_id] = group.get("categories")
                
                # Merge categories into groups_with_people
                groups = []
                for group in groups_with_people:
                    group_id = group.get("id")
                    if group_id in categories_by_group_id:
                        group["categories"] = categories_by_group_id[group_id]
                    groups.append(group)
                
                for group in groups:
                    group_id = str(group.get("id", ""))
                    if group_id not in request.group_ids:
                        continue
                    
                    # Exclude groups with excluded categories
                    if group_has_excluded_category(group, excluded_group_category_ids):
                        continue
                    
                    group_name = group.get("name", "Unknown Group")
                    leaders = get_leaders_from_group(group)
                    
                    for person in leaders:
                        person_id = person.get("id")
                        if not person_id:
                            continue
                        
                        if person_id not in filtered_people:
                            filtered_people[person_id] = {
                                "id": person_id,
                                "firstname": person.get("firstname", ""),
                                "preferred_name": person.get("preferred_name", ""),
                                "lastname": person.get("lastname", ""),
                                "email": person.get("email", ""),
                                "groups": [],
                                "service_positions": []
                            }
                        
                        existing = next(
                            (g for g in filtered_people[person_id]["groups"] if g["id"] == group_id),
                            None
                        )
                        if not existing:
                            filtered_people[person_id]["groups"].append({
                                "id": group_id,
                                "name": group_name,
                                "role": "Leader"
                            })
            except Exception as e:
                print(f"Error processing groups: {str(e)}")
        
        # Process volunteer positions - from people's departments
        if request.service_position_ids:
            try:
                people = client.get_all_people_with_departments(
                    adults_only=True,
                    excluded_category_ids=excluded_category_ids
                )
                
                for person in people:
                    person_id = person.get("id")
                    if not person_id:
                        continue
                    
                    person_positions = get_person_positions_from_departments(person)
                    
                    matched_positions = [
                        pos for pos in person_positions 
                        if pos["id"] in request.service_position_ids
                    ]
                    
                    if matched_positions:
                        if person_id not in filtered_people:
                            filtered_people[person_id] = {
                                "id": person_id,
                                "firstname": person.get("firstname", ""),
                                "preferred_name": person.get("preferred_name", ""),
                                "lastname": person.get("lastname", ""),
                                "email": person.get("email", ""),
                                "groups": [],
                                "service_positions": []
                            }
                        
                        for pos in matched_positions:
                            existing = next(
                                (p for p in filtered_people[person_id]["service_positions"] if p["id"] == pos["id"]),
                                None
                            )
                            if not existing:
                                filtered_people[person_id]["service_positions"].append({
                                    "id": pos["id"],
                                    "name": pos["name"],
                                    "department": pos.get("department", "")
                                })
            except Exception as e:
                import traceback
                print(f"Error processing volunteer positions: {str(e)}")
                print(traceback.format_exc())
        
        result = list(filtered_people.values())
        
        return {
            "people": result,
            "count": len(result)
        }
    except Exception as e:
        import traceback
        print(f"Error in filter_people: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
