import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./ObligationForms.css";

const FlexibleObligationForm = () => {
  const { id } = useParams(); // Will be undefined for add, contains the obligation ID for edit
  const isEditMode = !!id;
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    weekly_target_hours: 5,
    start_date: "", // New field
    end_date: "", // New field
    priority: 3, // New field
    constraints: {
      preferred_time_blocks: [],
      unavailable_days: []
    }
  });
  
  const [loading, setLoading] = useState(isEditMode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  
  // Fetch obligation data if in edit mode
  useEffect(() => {
    if (isEditMode) {
      fetchObligationData();
    }
  }, [id]);
  
  const fetchObligationData = async () => {
    try {
      const token = localStorage.getItem("accessToken");
      
      if (!token) {
        navigate("/login");
        return;
      }
      
      const response = await fetch(`/api/tasks/flexible/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (response.status === 401) {
        localStorage.removeItem("accessToken");
        navigate("/login");
        return;
      }
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const obligation = await response.json();
      
      setFormData({
        name: obligation.name || "",
        description: obligation.description || "",
        weekly_target_hours: obligation.weekly_target_hours || 5,
        start_date: obligation.start_date || "", // New field
        end_date: obligation.end_date || "", // New field
        priority: obligation.priority || 3, // New field
        constraints: obligation.constraints || {
          preferred_time_blocks: [],
          unavailable_days: []
        }
      });
      
      setLoading(false);
    } catch (err) {
      console.error("Error fetching obligation:", err);
      setError("Failed to load obligation data. Please try again.");
      setLoading(false);
    }
  };
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    if (name === "weekly_target_hours" || name === "priority") {
      setFormData(prev => ({
        ...prev,
        [name]: parseFloat(value)
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };
  
  // Handle changes to the constraints object
  const handleConstraintChange = (e) => {
    const { name, value, checked } = e.target;
    
    if (name === "unavailable_days") {
      let updatedDays = [...formData.constraints.unavailable_days];
      
      if (checked) {
        // Add the day if it's not already in the array
        if (!updatedDays.includes(value)) {
          updatedDays.push(value);
        }
      } else {
        // Remove the day from the array
        updatedDays = updatedDays.filter(day => day !== value);
      }
      
      setFormData(prev => ({
        ...prev,
        constraints: {
          ...prev.constraints,
          unavailable_days: updatedDays
        }
      }));
    } else if (name === "preferred_time") {
      // Handle preferred time block changes
      const [timeBlock, isPreferred] = value.split('-');
      let updatedTimeBlocks = [...formData.constraints.preferred_time_blocks];
      
      if (isPreferred === "true" && !updatedTimeBlocks.includes(timeBlock)) {
        updatedTimeBlocks.push(timeBlock);
      } else if (isPreferred === "false") {
        updatedTimeBlocks = updatedTimeBlocks.filter(block => block !== timeBlock);
      }
      
      setFormData(prev => ({
        ...prev,
        constraints: {
          ...prev.constraints,
          preferred_time_blocks: updatedTimeBlocks
        }
      }));
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    
    try {
      const token = localStorage.getItem("accessToken");
      
      if (!token) {
        navigate("/login");
        return;
      }
      
      const apiUrl = isEditMode 
        ? `/api/tasks/flexible/${id}` 
        : "/api/tasks/flexible";
      
      const method = isEditMode ? "PUT" : "POST";
      
      const response = await fetch(apiUrl, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
      }
      
      // Navigate back to dashboard on success
      navigate("/dashboard");
    } catch (err) {
      console.error("Error submitting obligation:", err);
      setError(err.message);
      setSubmitting(false);
    }
  };
  
  if (loading) {
    return (
      <div className="obligation-form-container loading">
        <div className="spinner"></div>
        <p>Loading obligation data...</p>
      </div>
    );
  }

  return (
    <div className="obligation-form-container">
      <div className="obligation-form-header">
        <h1>{isEditMode ? "Edit Flexible Obligation" : "Add Flexible Obligation"}</h1>
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          Back to Dashboard
        </button>
      </div>
      
      {error && <div className="form-error">{error}</div>}
      
      <form onSubmit={handleSubmit} className="obligation-form">
        <div className="form-group">
          <label htmlFor="name">Obligation Name</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            required
          />
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows="3"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="weekly_target_hours">Weekly Target Hours</label>
          <input
            type="number"
            id="weekly_target_hours"
            name="weekly_target_hours"
            step="0.5"
            min="0.5"
            max="40"
            value={formData.weekly_target_hours}
            onChange={handleInputChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Unavailable Days</label>
          <div className="checkbox-group">
            {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map(day => (
              <label key={day} className="checkbox-label">
                <input
                  type="checkbox"
                  name="unavailable_days"
                  value={day}
                  checked={formData.constraints.unavailable_days.includes(day)}
                  onChange={handleConstraintChange}
                />
                {day}
              </label>
            ))}
          </div>
        </div>
        
        <div className="form-group">
          <label>Preferred Time Blocks</label>
          <div className="checkbox-group">
            {[
              {value: "morning", label: "Morning (8AM-12PM)"},
              {value: "afternoon", label: "Afternoon (12PM-5PM)"},
              {value: "evening", label: "Evening (5PM-9PM)"},
              {value: "night", label: "Night (9PM-12AM)"}
            ].map(timeBlock => (
              <label key={timeBlock.value} className="checkbox-label">
                <input
                  type="checkbox"
                  name="preferred_time"
                  value={`${timeBlock.value}-${!formData.constraints.preferred_time_blocks.includes(timeBlock.value)}`}
                  checked={formData.constraints.preferred_time_blocks.includes(timeBlock.value)}
                  onChange={handleConstraintChange}
                />
                {timeBlock.label}
              </label>
            ))}
          </div>
        </div>
        
        <div className="form-group">
          <label>Start Date (Optional)</label>
          <input
            type="date"
            name="start_date"
            value={formData.start_date}
            onChange={handleInputChange}
          />
        </div>
        
        <div className="form-group">
          <label>End Date (Optional)</label>
          <input
            type="date"
            name="end_date"
            value={formData.end_date}
            onChange={handleInputChange}
          />
        </div>
        
        <div className="form-group">
          <label>Priority (1-5)</label>
          <input
            type="number"
            name="priority"
            min="1"
            max="5"
            value={formData.priority}
            onChange={handleInputChange}
          />
        </div>
        
        <div className="form-actions">
          <button
            type="button"
            className="cancel-btn"
            onClick={() => navigate("/dashboard")}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="submit-btn"
            disabled={submitting}
          >
            {submitting ? "Saving..." : (isEditMode ? "Update Obligation" : "Add Obligation")}
          </button>
        </div>
      </form>
    </div>
  );
};

export default FlexibleObligationForm;