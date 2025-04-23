import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./ObligationForms.css";

const FixedObligationForm = ({ onSubmit, initialData = {} }) => {
  const { id } = useParams(); // Will be undefined for add, contains the obligation ID for edit
  const isEditMode = !!id;
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    name: initialData.name || "",
    description: initialData.description || "",
    start_time: initialData.start_time || "",
    end_time: initialData.end_time || "",
    days_of_week: initialData.days_of_week || [],  // Now an array
    start_date: initialData.start_date || "",
    end_date: initialData.end_date || "",
    recurrence: initialData.recurrence || "weekly",
    priority: initialData.priority || 3
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
      
      const response = await fetch(`/api/tasks/fixed/${id}`, {
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
      
      // Format time values for the input field (HH:MM)
      const formatTime = (timeString) => {
        if (!timeString) return "";
        return timeString.substring(0, 5); // Get HH:MM part
      };
      
      setFormData({
        name: obligation.name || "",
        description: obligation.description || "",
        start_time: formatTime(obligation.start_time),
        end_time: formatTime(obligation.end_time),
        days_of_week: obligation.days_of_week || [],
        start_date: obligation.start_date || "",
        end_date: obligation.end_date || "",
        recurrence: obligation.recurrence || "weekly",
        priority: obligation.priority || 3
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
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDaysChange = (day) => {
    setFormData(prev => {
      const currentDays = [...prev.days_of_week];
      if (currentDays.includes(day)) {
        return { ...prev, days_of_week: currentDays.filter(d => d !== day) };
      } else {
        return { ...prev, days_of_week: [...currentDays, day] };
      }
    });
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
        ? `/api/tasks/fixed/${id}` 
        : "/api/tasks/fixed";
      
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
        <h1>{isEditMode ? "Edit Fixed Obligation" : "Add Fixed Obligation"}</h1>
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          Back to Dashboard
        </button>
      </div>
      
      {error && <div className="form-error">{error}</div>}
      
      <form onSubmit={handleSubmit} className="obligation-form">
        <div className="form-group">
          <label htmlFor="name">Name</label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            rows="3"
          />
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="start_time">Start Time</label>
            <input
              type="time"
              id="start_time"
              name="start_time"
              value={formData.start_time}
              onChange={handleInputChange}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="end_time">End Time</label>
            <input
              type="time"
              id="end_time"
              name="end_time"
              value={formData.end_time}
              onChange={handleInputChange}
              required
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="start_date">Start Date</label>
            <input
              type="date"
              id="start_date"
              name="start_date"
              value={formData.start_date}
              onChange={handleInputChange}
            />
          </div>

          <div className="form-group">
            <label htmlFor="end_date">End Date</label>
            <input
              type="date"
              id="end_date"
              name="end_date"
              value={formData.end_date}
              onChange={handleInputChange}
            />
          </div>
        </div>
        
        <div className="form-group">
          <label>Days of Week:</label>
          {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(day => (
            <label key={day}>
              <input
                type="checkbox"
                checked={formData.days_of_week.includes(day)}
                onChange={() => handleDaysChange(day)}
              />
              {day}
            </label>
          ))}
        </div>
        
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="recurrence">Recurrence</label>
            <select
              id="recurrence"
              name="recurrence"
              value={formData.recurrence}
              onChange={handleInputChange}
            >
              <option value="weekly">Weekly</option>
              <option value="biweekly">Biweekly</option>
              <option value="monthly">Monthly</option>
              <option value="once">Once</option>
            </select>
          </div>
        </div>
        
        <div className="form-group">
          <label htmlFor="priority">Priority (1-5)</label>
          <input
            type="range"
            id="priority"
            name="priority"
            min="1"
            max="5"
            value={formData.priority}
            onChange={handleInputChange}
          />
          <div className="priority-labels">
            <span>Lower</span>
            <span>Current: {formData.priority}</span>
            <span>Higher</span>
          </div>
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

export default FixedObligationForm;