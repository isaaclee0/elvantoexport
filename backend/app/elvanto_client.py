import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class ElvantoClient:
    def __init__(self, api_key: str = None):
        # Use provided API key or fall back to env (for backwards compatibility)
        self.api_key = api_key or os.getenv("ELVANTO_API_KEY")
        if not self.api_key:
            raise ValueError("Elvanto API key is required")
        self.api_url = os.getenv("ELVANTO_API_URL", "https://api.elvanto.com/v1")
        self.auth = (self.api_key, "x")
    
    def _make_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a POST request to the Elvanto API (per API documentation)"""
        url = f"{self.api_url}/{endpoint}.json"
        try:
            # Elvanto API uses POST with JSON body for all requests
            response = requests.post(
                url,
                auth=self.auth,
                json=data or {},
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            # Check for Elvanto API errors
            if "status" in result and result.get("status") != "ok":
                error_msg = result.get("error", {}).get("message", "Unknown Elvanto API error")
                raise Exception(f"Elvanto API error: {error_msg}")
            
            return result
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")
    
    def _to_int(self, value, default=0):
        """Convert value to int safely"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_all_groups_with_people(self) -> List[Dict]:
        """Get all groups from Elvanto with people field included"""
        all_groups = []
        page = 1
        page_size = 100
        
        while True:
            result = self._make_request("groups/getAll", {
                "page": page,
                "page_size": page_size,
                "fields": ["people"]
            })
            groups_data = result.get("groups", {})
            
            if not groups_data:
                break
                
            groups = groups_data.get("group", [])
            
            if not groups:
                break
            
            # Handle single group vs list
            if isinstance(groups, dict):
                groups = [groups]
            
            all_groups.extend(groups)
            
            # Check pagination - convert to int for comparison
            total = self._to_int(groups_data.get("total", 0))
            per_page = self._to_int(groups_data.get("per_page", page_size))
            on_this_page = self._to_int(groups_data.get("on_this_page", len(groups)))
            
            # Stop if we got fewer than expected or we have all records
            if on_this_page < per_page or len(all_groups) >= total:
                break
            page += 1
        
        return all_groups
    
    def get_all_groups_with_categories(self) -> List[Dict]:
        """Get all groups from Elvanto with categories field included"""
        all_groups = []
        page = 1
        page_size = 100
        
        while True:
            result = self._make_request("groups/getAll", {
                "page": page,
                "page_size": page_size,
                "fields": ["categories"]
            })
            groups_data = result.get("groups", {})
            
            if not groups_data:
                break
                
            groups = groups_data.get("group", [])
            
            if not groups:
                break
            
            # Handle single group vs list
            if isinstance(groups, dict):
                groups = [groups]
            
            all_groups.extend(groups)
            
            # Check pagination - convert to int for comparison
            total = self._to_int(groups_data.get("total", 0))
            per_page = self._to_int(groups_data.get("per_page", page_size))
            on_this_page = self._to_int(groups_data.get("on_this_page", len(groups)))
            
            # Stop if we got fewer than expected or we have all records
            if on_this_page < per_page or len(all_groups) >= total:
                break
            page += 1
        
        return all_groups
    
    def get_all_categories(self) -> List[Dict]:
        """Get all people categories from Elvanto"""
        try:
            result = self._make_request("people/categories/getAll", {})
            categories_data = result.get("categories", {})
            categories = categories_data.get("category", [])
            if isinstance(categories, dict):
                categories = [categories]
            return categories
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []
    
    def get_all_group_categories(self) -> List[Dict]:
        """Get all group categories from Elvanto"""
        try:
            result = self._make_request("groups/categories/getAll", {})
            categories_data = result.get("categories", {})
            categories = categories_data.get("category", [])
            if isinstance(categories, dict):
                categories = [categories]
            return categories
        except Exception as e:
            print(f"Error fetching group categories: {e}")
            return []
    
    def should_include_person(self, person: Dict, excluded_category_ids: List[str] = None) -> bool:
        """
        Check if a person should be included based on all criteria:
        - Not archived
        - Not in excluded categories
        - Is an adult (not marked as "Children")
        """
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
        if not self._is_adult(person):
            return False
        
        return True
    
    def _is_adult(self, person: Dict) -> bool:
        """
        Check if a person should be included as an adult.
        - Include if demographics has 'Adults'
        - Include if no demographics are set (assume adult)
        - Exclude only if explicitly marked as 'Children' (and not also 'Adults')
        """
        demographics = person.get("demographics", {})
        if not demographics or not isinstance(demographics, dict):
            # No demographics set - assume they're an adult
            return True
        
        demo_list = demographics.get("demographic", [])
        if isinstance(demo_list, dict):
            demo_list = [demo_list]
        
        if not demo_list:
            # Empty demographics list - assume adult
            return True
        
        demo_names = [d.get("name", "").lower() for d in demo_list]
        
        # If explicitly marked as Adults, include
        if "adults" in demo_names:
            return True
        
        # If explicitly marked as Children (and not Adults), exclude
        if "children" in demo_names:
            return False
        
        # Any other demographics (Families, Youth, etc.) - include
        return True
    
    def get_all_people_with_departments(self, adults_only: bool = True, excluded_category_ids: List[str] = None) -> List[Dict]:
        """Get all people from Elvanto with departments field to find all rostered volunteers"""
        all_people = []
        page = 1
        page_size = 100
        
        while True:
            request_data = {
                "page": page,
                "page_size": page_size,
                "fields": ["departments", "demographics"]  # Include demographics to filter adults
            }
            if page == 1:
                print(f"DEBUG: People with departments request (adults_only={adults_only})")
            result = self._make_request("people/getAll", request_data)
            people_data = result.get("people", {})
            
            if not people_data:
                break
                
            people = people_data.get("person", [])
            
            if not people:
                break
            
            # Handle single person vs list
            if isinstance(people, dict):
                people = [people]
            
            # Filter based on all criteria (archived, category, demographics)
            if adults_only:
                people = [p for p in people if self.should_include_person(p, excluded_category_ids)]
            
            all_people.extend(people)
            
            # Check pagination
            total = self._to_int(people_data.get("total", 0))
            per_page = self._to_int(people_data.get("per_page", page_size))
            on_this_page = self._to_int(people_data.get("on_this_page", len(people)))
            
            if on_this_page < per_page or len(all_people) >= total:
                break
            page += 1
        
        print(f"DEBUG: Fetched {len(all_people)} adults with departments")
        return all_people
    
    def get_person_details(self, person_id: str) -> Dict:
        """Get detailed information about a specific person"""
        result = self._make_request("people/getInfo", {"id": person_id})
        return result.get("person", {})
    
    def extract_volunteer_positions_from_people(self, people: List[Dict]) -> Dict[str, Dict]:
        """
        Extract all unique volunteer positions from people's department assignments.
        This gives us everyone who is ROSTERED for each position, not just scheduled.
        Returns a dict of position_key -> {name, department, volunteers: [...]}
        """
        positions = {}
        
        for person in people:
            person_id = person.get("id")
            if not person_id:
                continue
            
            depts = person.get("departments", {})
            if not depts or not isinstance(depts, dict):
                continue
            
            dept_list = depts.get("department", [])
            if isinstance(dept_list, dict):
                dept_list = [dept_list]
            
            for dept in dept_list:
                dept_name = dept.get("name", "Unknown")
                
                # Get sub-departments
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
                    
                    # Get positions
                    positions_data = sub.get("positions", {})
                    if not positions_data or not isinstance(positions_data, dict):
                        continue
                    
                    pos_list = positions_data.get("position", [])
                    if isinstance(pos_list, dict):
                        pos_list = [pos_list]
                    
                    for pos in pos_list:
                        pos_id = pos.get("id", "")
                        
                        # Use sub-department name as the position name
                        # This collapses all positions under a sub-department:
                        # "Preacher - Children's Talk" -> "Preacher"
                        # "Musicians - Bass" -> "Musicians"
                        # "Musicians - Vocals" -> "Musicians"
                        display_name = sub_name
                        
                        # Use sub-department name as key to group all positions in that sub-department
                        key = display_name
                        
                        if key not in positions:
                            positions[key] = {
                                "id": key,
                                "name": display_name,
                                "department": dept_name,
                                "position_ids": set(),
                                "volunteers": set()
                            }
                        
                        positions[key]["position_ids"].add(str(pos_id))
                        positions[key]["volunteers"].add(person_id)
        
        # Convert sets to lists for JSON serialization
        for key in positions:
            positions[key]["volunteers"] = list(positions[key]["volunteers"])
            positions[key]["position_ids"] = list(positions[key]["position_ids"])
        
        print(f"DEBUG: Found {len(positions)} unique volunteer positions")
        total_volunteers = sum(len(p["volunteers"]) for p in positions.values())
        print(f"DEBUG: Total rostered volunteers: {total_volunteers}")
        
        return positions
    
    def _add_item_positions(self, positions: Dict, item: Dict, service_type_name: str):
        """Extract volunteer position info from a service plan item"""
        # Item might be a heading with positions, or a position itself
        item_type = item.get("type", "")
        
        # If it's a heading, look for sub-items or positions
        if item_type == "heading":
            heading_name = item.get("heading", item.get("title", "Volunteers"))
            # Check for positions under this heading
            positions_data = item.get("positions", item.get("position", []))
            if positions_data:
                if isinstance(positions_data, dict):
                    positions_data = positions_data.get("position", [])
                if isinstance(positions_data, dict):
                    positions_data = [positions_data]
                for pos in positions_data:
                    self._add_position(positions, pos, f"{service_type_name} - {heading_name}")
        
        # If it's a position/role type, extract it
        elif item_type in ["position", "role", "volunteer"]:
            position_id = item.get("id", item.get("position_id"))
            position_name = item.get("title", item.get("name", "Position"))
            
            if position_id:
                if position_id not in positions:
                    positions[position_id] = {
                        "id": str(position_id),
                        "name": position_name,
                        "service_type": service_type_name,
                        "volunteers": set()
                    }
                
                # Get volunteers assigned to this position
                volunteers = item.get("volunteers", item.get("volunteer", []))
                if isinstance(volunteers, dict):
                    volunteers = volunteers.get("volunteer", [])
                if isinstance(volunteers, dict):
                    volunteers = [volunteers]
                
                for vol in volunteers:
                    person = vol.get("person", vol)
                    person_id = person.get("id")
                    if person_id:
                        positions[position_id]["volunteers"].add(person_id)
        
        # Check for nested items
        sub_items = item.get("items", item.get("item", []))
        if sub_items:
            if isinstance(sub_items, dict):
                sub_items = sub_items.get("item", [])
            if isinstance(sub_items, dict):
                sub_items = [sub_items]
            for sub_item in sub_items:
                self._add_item_positions(positions, sub_item, service_type_name)

    def _add_position(self, positions: Dict, position: Dict, service_type_name: str):
        """Helper to add a position and its volunteers"""
        position_id = position.get("id")
        position_name = position.get("name", "Unknown Position")
        
        if not position_id:
            return
        
        if position_id not in positions:
            positions[position_id] = {
                "id": str(position_id),
                "name": position_name,
                "service_type": service_type_name,
                "volunteers": set()
            }
        
        # Get volunteers - try different structures
        volunteers = position.get("volunteers", {})
        if isinstance(volunteers, dict):
            volunteer_list = volunteers.get("volunteer", [])
        elif isinstance(volunteers, list):
            volunteer_list = volunteers
        else:
            volunteer_list = []
        
        if isinstance(volunteer_list, dict):
            volunteer_list = [volunteer_list]
        
        for volunteer in volunteer_list:
            person = volunteer.get("person", volunteer)
            person_id = person.get("id")
            if person_id:
                positions[position_id]["volunteers"].add(person_id)
