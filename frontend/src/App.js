import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

function App() {
  const [apiKey, setApiKey] = useState('');
  const [apiKeySubmitted, setApiKeySubmitted] = useState(false);
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [categories, setCategories] = useState([]);
  const [excludedCategories, setExcludedCategories] = useState([]);
  const [groupCategories, setGroupCategories] = useState([]);
  const [excludedGroupCategories, setExcludedGroupCategories] = useState([]);
  const [allItems, setAllItems] = useState([]);  // Store all items (unfiltered)
  const [items, setItems] = useState([]);  // Filtered items for display
  const [selectedItems, setSelectedItems] = useState([]);
  const [filteredPeople, setFilteredPeople] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingPeople, setLoadingPeople] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState('');
  
  // Track initial loading state
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const [healthLoaded, setHealthLoaded] = useState(false);
  const [peopleCategoriesLoaded, setPeopleCategoriesLoaded] = useState(false);
  const [groupCategoriesLoaded, setGroupCategoriesLoaded] = useState(false);
  const [itemsLoaded, setItemsLoaded] = useState(false);

  // Reset all state when API key changes
  useEffect(() => {
    if (!apiKeySubmitted) {
      setStatus('loading');
      setMessage('');
      setCategories([]);
      setGroupCategories([]);
      setAllItems([]);
      setItems([]);
      setSelectedItems([]);
      setFilteredPeople([]);
      setInitialLoadComplete(false);
      setHealthLoaded(false);
      setPeopleCategoriesLoaded(false);
      setGroupCategoriesLoaded(false);
      setItemsLoaded(false);
      setError(null);
    }
  }, [apiKeySubmitted]);

  // Fetch health status
  useEffect(() => {
    if (!apiKeySubmitted) return;
    
    fetch(`${API_URL}/health`)
      .then(response => response.json())
      .then(data => {
        setStatus('connected');
        setMessage(data.status || 'Backend is healthy');
        setHealthLoaded(true);
      })
      .catch(error => {
        setStatus('error');
        setMessage(`Failed to fetch: ${error.message}`);
        setHealthLoaded(true);  // Still mark as loaded even on error
      });
  }, [apiKeySubmitted]);

  // Fetch people categories
  useEffect(() => {
    if (!apiKeySubmitted) return;
    
    fetch(`${API_URL}/api/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    })
      .then(response => response.json())
      .then(data => {
        setCategories(data.categories || []);
        setPeopleCategoriesLoaded(true);
      })
      .catch(error => {
        console.error('Error loading categories:', error);
        setPeopleCategoriesLoaded(true);  // Still mark as loaded even on error
      });
  }, [apiKey, apiKeySubmitted]);

  // Fetch group categories
  useEffect(() => {
    if (!apiKeySubmitted) return;
    
    fetch(`${API_URL}/api/group-categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    })
      .then(response => response.json())
      .then(data => {
        setGroupCategories(data.categories || []);
        setGroupCategoriesLoaded(true);
      })
      .catch(error => {
        console.error('Error loading group categories:', error);
        setGroupCategoriesLoaded(true);  // Still mark as loaded even on error
      });
  }, [apiKey, apiKeySubmitted]);

  // Fetch groups and positions once on load
  useEffect(() => {
    if (!apiKeySubmitted) return;
    
    const fetchItems = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_URL}/api/groups-and-services`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: apiKey, excluded_group_category_ids: [] }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setAllItems(data.items || []);  // Store all items
        setMessage(`Loaded ${data.count || 0} items`);
        setItemsLoaded(true);
      } catch (error) {
        console.error('Error loading data:', error);
        setError(`Failed to load data: ${error.message}`);
        setItemsLoaded(true);  // Still mark as loaded even on error
      } finally {
        setLoading(false);
      }
    };
    
    fetchItems();
  }, [apiKey, apiKeySubmitted]);  // Fetch when API key is submitted

  // Check if all initial data is loaded
  useEffect(() => {
    if (healthLoaded && peopleCategoriesLoaded && groupCategoriesLoaded && itemsLoaded) {
      setInitialLoadComplete(true);
    }
  }, [healthLoaded, peopleCategoriesLoaded, groupCategoriesLoaded, itemsLoaded]);

  // Filter items client-side based on excluded group categories
  useEffect(() => {
    if (excludedGroupCategories.length === 0) {
      // No exclusions, show all items
      setItems(allItems);
    } else {
      // Filter out groups with excluded categories
      const filtered = allItems.filter(item => {
        if (item.type !== 'group') {
          // Service positions are always shown
          return true;
        }
        
        // Check if group has any excluded category
        const groupCategoryIds = item.category_ids || [];
        const hasExcludedCategory = groupCategoryIds.some(catId => 
          excludedGroupCategories.includes(catId)
        );
        
        return !hasExcludedCategory;
      });
      
      setItems(filtered);
      
      // Uncheck any items that are now hidden
      setSelectedItems(prev => {
        const visibleItemIds = new Set(filtered.map(item => item.id));
        return prev.filter(id => visibleItemIds.has(id));
      });
    }
  }, [allItems, excludedGroupCategories]);

  const handleCategoryToggle = (categoryId) => {
    setExcludedCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
    // Clear filtered results since exclusions changed (but keep selection)
    setFilteredPeople([]);
  };

  const handleGroupCategoryToggle = (categoryId) => {
    setExcludedGroupCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
    // Clear filtered results since groups list changed
    // Note: selectedItems will be automatically cleaned by the useEffect
    setFilteredPeople([]);
  };

  const handleApiKeySubmit = (e) => {
    e.preventDefault();
    if (apiKey.trim()) {
      setApiKeySubmitted(true);
      setError(null);
    }
  };

  const handleApiKeyReset = () => {
    setApiKey('');
    setApiKeySubmitted(false);
  };

  const handleItemToggle = (itemId) => {
    setSelectedItems(prev => {
      if (prev.includes(itemId)) {
        return prev.filter(id => id !== itemId);
      } else {
        return [...prev, itemId];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedItems.length === items.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(items.map(item => item.id));
    }
  };

  const handleFilter = async () => {
    if (selectedItems.length === 0) {
      alert('Please select at least one group or volunteer position');
      return;
    }

    setLoadingPeople(true);
    setError(null);
    setProgress('Filtering people... This may take a moment.');
    setFilteredPeople([]);
    
    const groupIds = items
      .filter(item => item.type === 'group' && selectedItems.includes(item.id))
      .map(item => item.id);
    
    const servicePositionIds = items
      .filter(item => item.type === 'service' && selectedItems.includes(item.id))
      .map(item => item.id);

    try {
      const response = await fetch(`${API_URL}/api/filter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey,
          group_ids: groupIds,
          service_position_ids: servicePositionIds,
          excluded_category_ids: excludedCategories,
          excluded_group_category_ids: excludedGroupCategories,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setFilteredPeople(data.people || []);
      setProgress('');
    } catch (error) {
      console.error('Error filtering people:', error);
      setError(`Error filtering people: ${error.message}`);
      setProgress('');
    } finally {
      setLoadingPeople(false);
    }
  };

  const handleExport = async () => {
    if (filteredPeople.length === 0) {
      alert('No people to export. Please filter first.');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/export/xlsx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ people: filteredPeople }),
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'elvanto_export.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      alert('Error exporting: ' + error.message);
    }
  };

  // Show API key form if not submitted
  if (!apiKeySubmitted) {
    return (
      <div className="App">
        <div className="api-key-screen">
          <div className="api-key-content">
            <h1>Elvanto Export</h1>
            <p className="api-key-description">
              Enter your Elvanto API key to get started. Your API key is used only for this session and is not stored.
            </p>
            <form onSubmit={handleApiKeySubmit} className="api-key-form">
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Elvanto API key"
                className="api-key-input"
                required
              />
              <button type="submit" className="api-key-submit">
                Connect
              </button>
            </form>
            {error && <div className="error-message">{error}</div>}
            <p className="api-key-hint">
              You can find your API key in your Elvanto account settings.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Show loading screen until all initial data is loaded
  if (!initialLoadComplete) {
    return (
      <div className="App">
        <div className="loading-screen">
          <div className="loading-content">
            <div className="spinner"></div>
            <h2>Loading Elvanto Export</h2>
            <p>Please wait while we fetch your data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div>
            <h1>Elvanto Export</h1>
            <p className="status">
              Backend: <span className={status}>{status}</span> • {message}
            </p>
          </div>
          <button onClick={handleApiKeyReset} className="reset-api-key-btn" title="Change API key">
            Change API Key
          </button>
        </div>
      </header>

      <main className="App-main">
        {error && <div className="error-message">{error}</div>}
        {progress && <div className="progress-message">{progress}</div>}

        {/* People Category Exclusion Section */}
        {categories.length > 0 && (
          <section className="categories-section">
            <div className="section-header">
              <h2>Exclude People Categories</h2>
              <span className="section-hint">People in checked categories will be excluded</span>
            </div>
            <div className="categories-grid">
              {categories.map(cat => (
                <label key={cat.id} className={`category-label ${excludedCategories.includes(cat.id) ? 'excluded' : ''}`}>
                  <input
                    type="checkbox"
                    checked={excludedCategories.includes(cat.id)}
                    onChange={() => handleCategoryToggle(cat.id)}
                  />
                  <span className="category-name">{cat.name}</span>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* Group Category Exclusion Section */}
        {groupCategories.length > 0 && (
          <section className="categories-section group-categories-section">
            <div className="section-header">
              <h2>Exclude Group Categories</h2>
              <span className="section-hint">Groups in checked categories will be excluded</span>
            </div>
            <div className="categories-grid">
              {groupCategories.map(cat => (
                <label key={cat.id} className={`category-label ${excludedGroupCategories.includes(cat.id) ? 'excluded' : ''}`}>
                  <input
                    type="checkbox"
                    checked={excludedGroupCategories.includes(cat.id)}
                    onChange={() => handleGroupCategoryToggle(cat.id)}
                  />
                  <span className="category-name">{cat.name}</span>
                </label>
              ))}
            </div>
          </section>
        )}

        <section className="selection-section">
          <div className="section-header">
            <h2>Select Groups / Volunteer Positions</h2>
            <div className="header-actions">
              <button onClick={handleSelectAll} className="select-all-btn">
                {selectedItems.length === items.length ? 'Clear All' : 'Select All'}
              </button>
              <button 
                onClick={handleFilter} 
                disabled={selectedItems.length === 0 || loadingPeople}
                className="filter-btn"
              >
                {loadingPeople ? 'Loading...' : `Get People (${selectedItems.length})`}
              </button>
            </div>
          </div>
          
          {loading ? (
            <p className="loading-text">Loading...</p>
          ) : items.length === 0 ? (
            <p className="no-items">No groups or volunteer positions found</p>
          ) : (
            <div className="items-grid">
              {items.map(item => (
                <label key={item.id} className={`item-label ${selectedItems.includes(item.id) ? 'selected' : ''}`}>
                  <input
                    type="checkbox"
                    checked={selectedItems.includes(item.id)}
                    onChange={() => handleItemToggle(item.id)}
                  />
                  <span className="item-text">
                    <span className="item-name">{item.name}</span>
                    <span className={`item-badge ${item.type}`}>{item.type}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </section>

        {filteredPeople.length > 0 && (
          <section className="results-section">
            <div className="section-header">
              <h2>People ({filteredPeople.length})</h2>
              <button onClick={handleExport} className="export-btn">
                Export to XLSX
              </button>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Groups / Positions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPeople.map(person => (
                    <tr key={person.id}>
                      <td>
                        {person.preferred_name || person.firstname} {person.lastname}
                      </td>
                      <td>{person.email || '-'}</td>
                      <td>
                        {[
                          ...(person.groups || []).map(g => `${g.name} (${g.role})`),
                          ...(person.service_positions || []).map(p => `${p.name}`)
                        ].join(', ') || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
