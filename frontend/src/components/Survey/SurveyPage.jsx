import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import QuestionCard from "./QuestionCard";
import "./Survey.css";

function SurveyPage() {
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch survey questions from backend
    fetchSurveyQuestions();
  }, []);

  const fetchSurveyQuestions = async () => {
    setIsLoading(true);
    try {
      // Replace with your actual API endpoint
      const response = await fetch("/api/survey-questions");

      if (!response.ok) {
        throw new Error("Failed to fetch survey questions");
      }

      const data = await response.json();
      setQuestions(data);

      // Initialize answers object with empty values
      const initialAnswers = {};
      data.forEach((question) => {
        initialAnswers[question.id] = "";
      });
      setAnswers(initialAnswers);

      setIsLoading(false);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);

      // For development - use sample questions if API fails
      useSampleQuestions();
    }
  };

  // Sample questions for development/testing
  const useSampleQuestions = () => {
    const sampleQuestions = [
      {
        id: 1,
        question: "What time do you prefer to study?",
        type: "mcq",
        options: ["Morning", "Afternoon", "Evening", "Late night"],
      },
      {
        id: 2,
        question: "What time do you usually wake up?",
        type: "time",
      },
      {
        id: 3,
        question: "How long can you study before needing a break?",
        type: "mcq",
        options: ["30 minutes", "1 hour", "2 hours", "More than 2 hours"],
      },
      {
        id: 4,
        question: "What's your preferred study environment?",
        type: "mcq",
        options: ["Library", "Coffee shop", "Home", "Outdoors"],
      },
      {
        id: 5,
        question: "Do you have any specific times you're unavailable to study?",
        type: "text",
      },
    ];

    setQuestions(sampleQuestions);

    // Initialize answers object with empty values
    const initialAnswers = {};
    sampleQuestions.forEach((question) => {
      initialAnswers[question.id] = "";
    });
    setAnswers(initialAnswers);

    setIsLoading(false);
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // Submit answers and redirect to schedule page
      submitAnswersAndRedirect();
    }
  };

  const handleSkip = () => {
    // Skip all remaining questions and redirect to schedule page
    submitAnswersAndRedirect();
  };

  const handleAnswer = (questionId, answer) => {
    setAnswers({
      ...answers,
      [questionId]: answer,
    });
  };

  const token = localStorage.getItem("accessToken");

  const submitAnswersAndRedirect = async () => {
    try {
      // Submit answers to backend
      await fetch("/api/survey-answers", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ answers }),
      });

      // Redirect to schedule page
      navigate("/dashboard");
    } catch (err) {
      console.error("Failed to submit answers:", err);
      // Still redirect even if submission fails
      navigate("/dashboard");
    }
  };

  if (isLoading) {
    return (
      <div className="survey-loading">
        <div className="loading-spinner"></div>
        <p>Loading survey questions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="survey-error">
        <h2>Something went wrong</h2>
        <p>{error}</p>
        <button onClick={() => navigate("/dashboard")} className="skip-button">
          Continue to Dashboard
        </button>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex];
  const isLastQuestion = currentQuestionIndex === questions.length - 1;

  return (
    <div className="survey-container">
      <div className="survey-header">
        <div className="survey-progress">
          <div className="progress-text">
            Question {currentQuestionIndex + 1} of {questions.length}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${
                  ((currentQuestionIndex + 1) / questions.length) * 100
                }%`,
              }}
            ></div>
          </div>
        </div>
        <button onClick={handleSkip} className="skip-button">
          Skip Survey
        </button>
      </div>

      {currentQuestion && (
        <QuestionCard
          question={currentQuestion}
          answer={answers[currentQuestion.id]}
          onAnswer={(answer) => handleAnswer(currentQuestion.id, answer)}
          onSubmit={handleNextQuestion}
          isLastQuestion={isLastQuestion}
        />
      )}
    </div>
  );
}

export default SurveyPage;
