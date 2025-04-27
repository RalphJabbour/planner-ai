import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./MaterialsQuiz.css";

const StudyTimeEstimator = () => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [serviceStatus, setServiceStatus] = useState({ available: null, checked: false });
  const [estimatedHours, setEstimatedHours] = useState(null);
  const [explanation, setExplanation] = useState("");
  const [documentId, setDocumentId] = useState(null);
  const [creationSuccess, setCreationSuccess] = useState(false);
  const [deadline, setDeadline] = useState("");
  const navigate = useNavigate();

  // Set default deadline to 2 weeks from now
  useEffect(() => {
    const twoWeeksFromNow = new Date();
    twoWeeksFromNow.setDate(twoWeeksFromNow.getDate() + 14);
    
    // Format as YYYY-MM-DD
    const year = twoWeeksFromNow.getFullYear();
    const month = String(twoWeeksFromNow.getMonth() + 1).padStart(2, '0');
    const day = String(twoWeeksFromNow.getDate()).padStart(2, '0');
    
    setDeadline(`${year}-${month}-${day}`);
  }, []);

  // Check if the service is available on component mount
  useEffect(() => {
    checkServiceAvailability();
  }, []);

  const checkServiceAvailability = async () => {
    try {
      // Try to reach the service with a simple HEAD request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
      
      await fetch("http://localhost:9001/", {
        method: "HEAD",
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      setServiceStatus({ available: true, checked: true });
    } catch (err) {
      console.error("Service availability check failed:", err);
      setServiceStatus({ available: false, checked: true });
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      setError(null);
    } else {
      setFile(null);
      setFileName("");
      setError("Please select a valid PDF file.");
    }
  };

  const handleEstimateTime = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError("Please select a PDF file to upload.");
      return;
    }

    // If service is known to be unavailable, don't even try
    if (serviceStatus.checked && !serviceStatus.available) {
      setError("The PDF analysis service is currently unavailable. Please try again later or contact support.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setEstimatedHours(null);
    setExplanation("");
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      // Add a timeout to the fetch request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      // Call the study time estimation endpoint
      const response = await fetch("http://localhost:9001/estimate-study-time", {
        method: "POST",
        body: formData,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      setEstimatedHours(result.estimated_hours);
      setExplanation(result.explanation);
      setDocumentId(result.document_id);
      
    } catch (err) {
      console.error("Error estimating study time:", err);
      
      // Use a more descriptive error message based on the error type
      if (err.name === 'AbortError') {
        setError("Request timed out. The PDF analysis service might be unavailable or overloaded.");
        setServiceStatus({ available: false, checked: true });
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        setError("Network error: The PDF analysis service is unavailable. Please try again later.");
        setServiceStatus({ available: false, checked: true });
      } else {
        setError(err.message || "Failed to estimate study time for the document.");
      }
      
      // Generate a fallback estimate based on file size if we can
      if (file) {
        const sizeInMB = file.size / (1024 * 1024);
        const fallbackHours = Math.max(1, Math.ceil(sizeInMB * 0.5)); // 0.5 hours per MB with minimum 1 hour
        
        setEstimatedHours(fallbackHours);
        setExplanation("This is a fallback estimate based on file size. The AI analysis service is currently unavailable.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateObligation = async () => {
    if (!estimatedHours) {
      setError("Please estimate study time first.");
      return;
    }

    if (!deadline) {
      setError("Please set a deadline for your study obligation.");
      return;
    }

    setLoading(true);
    
    try {
      // Get token from local storage
      const token = localStorage.getItem("accessToken");
      
      if (!token) {
        throw new Error("You must be logged in to create obligations.");
      }
      
      // Create a date object from the deadline and ensure it's in the correct format
      // Set the time to 23:59:59 on the deadline day (end of day)
      const deadlineDate = new Date(`${deadline}T23:59:59`);
      
      // Create a flexible obligation - using time without timezone to avoid comparison issues
      const obligationData = {
        name: `Study: ${fileName}`,
        description: `Study material from ${fileName}. ${explanation}`,
        weekly_target_hours: estimatedHours,
        start_date: new Date().toISOString().split('T')[0], // Just the date part (YYYY-MM-DD)
        end_date: deadlineDate.toISOString().split('T')[0], // Just the date part (YYYY-MM-DD)
        priority: 2 // Medium-high priority
      };
      
      console.log("Creating obligation with data:", obligationData);
      
      const response = await fetch("/api/tasks/flexible", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(obligationData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log("Created flexible obligation:", result);
      
      // Trigger schedule update
      try {
        const updateResponse = await fetch("/api/tasks/update-schedule", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          }
        });
        
        if (!updateResponse.ok) {
          console.warn("Schedule update failed, but obligation was created:", await updateResponse.text());
        } else {
          console.log("Schedule updated successfully");
        }
      } catch (updateErr) {
        console.warn("Error updating schedule:", updateErr);
        // We don't want to fail the overall operation if just the schedule update fails
      }
      
      setCreationSuccess(true);
      
    } catch (err) {
      console.error("Error creating obligation:", err);
      setError(err.message || "Failed to create the study obligation.");
    } finally {
      setLoading(false);
    }
  };
  
  const resetForm = () => {
    setFile(null);
    setFileName("");
    setEstimatedHours(null);
    setExplanation("");
    setDocumentId(null);
    setCreationSuccess(false);
    setError(null);
    
    // Reset deadline to two weeks from now
    const twoWeeksFromNow = new Date();
    twoWeeksFromNow.setDate(twoWeeksFromNow.getDate() + 14);
    
    // Format as YYYY-MM-DD
    const year = twoWeeksFromNow.getFullYear();
    const month = String(twoWeeksFromNow.getMonth() + 1).padStart(2, '0');
    const day = String(twoWeeksFromNow.getDate()).padStart(2, '0');
    
    setDeadline(`${year}-${month}-${day}`);
  };

  return (
    <div className="materials-quiz-container">
      <div className="materials-quiz-header">
        <h1>Study Time Estimator</h1>
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          Back to Dashboard
        </button>
      </div>
      
      {serviceStatus.checked && !serviceStatus.available && (
        <div className="service-warning">
          <h3>⚠️ Service Unavailable</h3>
          <p>The PDF analysis service is currently unavailable. You can still create study obligations with manual time estimates.</p>
        </div>
      )}
      
      {error && <div className="form-error">{error}</div>}
      
      {creationSuccess && (
        <div className="success-message">
          <h2>Success!</h2>
          <p>Study obligation for {fileName} has been created in your calendar.</p>
          <p>Estimated study time: {estimatedHours} hours</p>
          <p>Deadline: {new Date(deadline).toLocaleDateString()}</p>
          <button className="submit-btn" onClick={resetForm}>
            Estimate Another Document
          </button>
          <button className="secondary-btn" onClick={() => navigate("/schedule")}>
            View Schedule
          </button>
        </div>
      )}
      
      {!creationSuccess && (
        <div className="upload-section">
          <div className="upload-instructions">
            <h2>How it works</h2>
            <ol>
              <li>Upload your PDF document (assignment, notes, paper, etc.)</li>
              <li>Set a deadline for when you need to complete studying</li>
              <li>Our AI will analyze the document and estimate study time</li>
              <li>Click "Create Study Obligation" to add to your schedule</li>
              <li>The scheduler will automatically allocate time in your calendar</li>
            </ol>
          </div>
          
          <form onSubmit={handleEstimateTime} className="upload-form">
            <div className="file-input-container">
              <label htmlFor="pdf-upload" className="file-input-label">
                {fileName ? fileName : "Choose PDF file"}
              </label>
              <input
                type="file"
                id="pdf-upload"
                accept=".pdf"
                onChange={handleFileChange}
                className="file-input"
              />
            </div>
            
            <div className="form-group deadline-input">
              <label htmlFor="deadline">Study Deadline</label>
              <input
                type="date"
                id="deadline"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                min={new Date().toISOString().split('T')[0]} // Can't set deadline in the past
                className="deadline-picker"
              />
            </div>
            
            <button 
              type="submit" 
              className="submit-btn" 
              disabled={!file || loading}
            >
              {loading ? (
                <>
                  <div className="spinner-small"></div>
                  Processing...
                </>
              ) : (
                serviceStatus.checked && !serviceStatus.available 
                  ? "Use File Size Estimate" 
                  : "Estimate Study Time"
              )}
            </button>
          </form>
          
          {estimatedHours !== null && (
            <div className="estimation-results">
              <h3>Study Time Estimate</h3>
              <div className="estimate-box">
                <div className="estimate-hours">{estimatedHours} hours</div>
                <div className="estimate-explanation">{explanation}</div>
              </div>
              <button 
                className="submit-btn create-obligation-btn" 
                onClick={handleCreateObligation}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="spinner-small"></div>
                    Creating...
                  </>
                ) : (
                  "Create Study Obligation"
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StudyTimeEstimator; 