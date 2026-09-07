import AuthPage from "./AuthPage";

function Login({ onLoginSuccess, onBackToHome }) {
  return (
    <AuthPage
      initialMode="login"
      onLoginSuccess={onLoginSuccess}
      onBackToHome={onBackToHome}
    />
  );
}

export default Login;