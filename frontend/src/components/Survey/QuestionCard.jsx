import React, { useState } from "react";

function QuestionCard({
  question,
  answer,
  onAnswer,
  onSubmit,
  isLastQuestion,
}) {
  // For time input validation
  const [timeError, setTimeError] = useState("");

  const handleInputChange = (value) => {
    if (question.type === "time") {
      // Validate time format (optional)
      const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
      if (value && !timeRegex.test(value)) {
        setTimeError("Please enter a valid time (HH:MM)");
      } else {
        setTimeError("");
      }
    }

    onAnswer(value);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // For time type, validate before submitting
    if (question.type === "time" && timeError) {
      return;
    }

    onSubmit();
  };

  return (
    <div className="question-card">
      <h2 className="question-text">{question.question}</h2>

      <form onSubmit={handleSubmit} className="question-form">
        {question.type === "mcq" && (
          <div className="mcq-options">
            {question.options.map((option, index) => (
              <div className="option-item" key={index}>
                <input
                  type="radio"
                  id={`option-${index}`}
                  name="mcq-answer"
                  value={option}
                  checked={answer === option}
                  onChange={() => handleInputChange(option)}
                />
                <label htmlFor={`option-${index}`}>{option}</label>
              </div>
            ))}
          </div>
        )}

        {question.type === "time" && (
          <div className="time-input">
            <input
              type="time"
              value={answer}
              onChange={(e) => handleInputChange(e.target.value)}
              required
            />
            {timeError && <div className="input-error">{timeError}</div>}
          </div>
        )}

        {question.type === "text" && (
          <div className="text-input">
            <textarea
              value={answer}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder="Type your answer here..."
              rows={4}
            />
          </div>
        )}

        <button
          type="submit"
          className="submit-button"
          disabled={question.type === "mcq" && !answer}
        >
          {isLastQuestion ? "Finish" : "Next"}
        </button>
      </form>
    </div>
  );
}

export default QuestionCard;
