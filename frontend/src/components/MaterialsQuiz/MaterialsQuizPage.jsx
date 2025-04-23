import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./MaterialsQuiz.css";

const MaterialsQuizPage = () => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [concepts, setConcepts] = useState([]);
  const [ratings, setRatings] = useState({});
  const [documentId, setDocumentId] = useState(null);
  const [step, setStep] = useState("upload"); // "upload", "rating", "complete"
  const navigate = useNavigate();

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

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError("Please select a PDF file to upload.");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      // Call the iep-quiz endpoint
      const response = await fetch("http://localhost:9001/extract-ideas", {
        method: "POST",
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.ideas && result.ideas.length > 0) {
        setConcepts(result.ideas);
        setDocumentId(result.document_id);
        
        // Initialize ratings object with zeroes
        const initialRatings = {};
        result.ideas.forEach(idea => {
          initialRatings[idea.concept] = 5; // Default to middle value (5)
        });
        setRatings(initialRatings);
        
        // Move to rating step
        setStep("rating");
      } else {
        setError("No concepts were extracted from the document. Please try a different PDF.");
      }
    } catch (err) {
      console.error("Error uploading document:", err);
      setError(err.message || "Failed to extract concepts from the document.");
    } finally {
      setLoading(false);
    }
  };
  
  const handleRatingChange = (concept, value) => {
    setRatings(prev => ({
      ...prev,
      [concept]: value
    }));
  };
  
  const handleSubmitRatings = async () => {
    setLoading(true);
    
    try {
      // Prepare data to send to backend
      const ratingData = {
        document_id: documentId,
        ratings: Object.entries(ratings).map(([concept, rating]) => ({
          concept,
          rating: parseInt(rating)
        }))
      };
      
      // This would normally send to your backend API
      // For now, just mock a successful submission
      console.log("Submitting ratings:", ratingData);
      
      // In a real implementation, you'd save this to your backend:
      /*
      const token = localStorage.getItem("accessToken");
      const response = await fetch("/api/materials/concept-ratings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(ratingData),
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      */
      
      // Move to complete step
      setStep("complete");
    } catch (err) {
      console.error("Error submitting ratings:", err);
      setError(err.message || "Failed to submit your concept ratings.");
    } finally {
      setLoading(false);
    }
  };
  
  const resetForm = () => {
    setFile(null);
    setFileName("");
    setConcepts([]);
    setRatings({});
    setDocumentId(null);
    setStep("upload");
    setError(null);
  };
  
  // Upload screen
  if (step === "upload") {
    return (
      <div className="materials-quiz-container">
        <div className="materials-quiz-header">
          <h1>Upload Learning Material</h1>
          <button className="back-btn" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
        
        {error && <div className="form-error">{error}</div>}
        
        <div className="upload-section">
          <div className="upload-instructions">
            <h2>How it works</h2>
            <ol>
              <li>Upload a PDF document (lecture notes, textbook chapter, etc.)</li>
              <li>Our AI will extract key concepts from the material</li>
              <li>Rate your knowledge of each concept on a scale of 1-10</li>
              <li>We'll provide personalized study recommendations</li>
            </ol>
          </div>
          
          <form onSubmit={handleUpload} className="upload-form">
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
                "Upload and Extract Concepts"
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }
  
  // Rating screen
  if (step === "rating") {
    return (
      <div className="materials-quiz-container">
        <div className="materials-quiz-header">
          <h1>Rate Your Knowledge</h1>
          <button className="back-btn" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
        
        {error && <div className="form-error">{error}</div>}
        
        <div className="concepts-rating-section">
          <p className="rating-instructions">
            For each concept extracted from <strong>{fileName}</strong>, rate your current knowledge level:
          </p>
          
          <div className="concepts-list">
            {concepts.map((idea, index) => (
              <div key={index} className="concept-rating-item">
                <h3 className="concept-title">{idea.concept}</h3>
                <div className="rating-container">
                  <div className="rating-labels">
                    <span>Unfamiliar</span>
                    <span>Expert</span>
                  </div>
                  <div className="rating-slider-container">
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={ratings[idea.concept]}
                      onChange={(e) => handleRatingChange(idea.concept, e.target.value)}
                      className="rating-slider"
                    />
                    <div className="rating-value">{ratings[idea.concept]}/10</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          <div className="form-actions">
            <button 
              className="cancel-btn" 
              onClick={resetForm}
            >
              Cancel
            </button>
            <button 
              className="submit-btn" 
              onClick={handleSubmitRatings}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="spinner-small"></div>
                  Submitting...
                </>
              ) : (
                "Submit Ratings"
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  // Complete screen
  if (step === "complete") {
    return (
      <div className="materials-quiz-container">
        <div className="materials-quiz-header">
          <h1>Concept Ratings Submitted</h1>
          <button className="back-btn" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
        
        <div className="completion-section">
          <div className="completion-icon">✓</div>
          <h2>Thank you for your ratings!</h2>
          <p>
            We've recorded your knowledge levels for the concepts in <strong>{fileName}</strong>.
            This information will be used to personalize your study recommendations.
          </p>
          
          <div className="completion-actions">
            <button 
              className="secondary-btn" 
              onClick={resetForm}
            >
              Rate Another Document
            </button>
            <button 
              className="primary-btn" 
              onClick={() => navigate("/dashboard")}
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return null; // Fallback
};

export default MaterialsQuizPage;