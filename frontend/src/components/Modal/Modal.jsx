import React from 'react';
import styles from './Modal.module.css';

const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  // Prevent clicks inside the modal from closing it
  const handleContentClick = (e) => {
    e.stopPropagation();
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={handleContentClick}>
        <div className={styles.modalHeader}>
          <h2>{title || 'Details'}</h2>
          <button className={styles.closeButton} onClick={onClose}>
            &times;
          </button>
        </div>
        <div className={styles.modalBody}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;