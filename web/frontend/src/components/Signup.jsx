import AuthPage from "./AuthPage";

function Signup({ onLoginSuccess, onBackToHome }) {
  return (
    <AuthPage
      initialMode="signup"
      onLoginSuccess={onLoginSuccess}
      onBackToHome={onBackToHome}
    />
  );
}

export default Signup;