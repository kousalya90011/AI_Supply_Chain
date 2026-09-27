function ErrorMessage({
  title = "Unable to load data",
  message = "Please check the backend connection and try again.",
  onRetry,
}) {
  return (
    <div className="error-panel">
      <div className="error-icon">!</div>

      <div className="error-content">
        <h3>{title}</h3>
        <p>{message}</p>

        {onRetry && (
          <button className="retry-button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

export default ErrorMessage;