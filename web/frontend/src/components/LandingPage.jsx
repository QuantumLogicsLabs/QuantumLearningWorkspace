import { useEffect, useRef, useState } from "react";
import ThemeToggle from "./ThemeToggle.jsx";
import "./LandingPage.css";

const FEATURES = [
  {
    icon: "📥",
    title: "Multi-Source Ingestion",
    body: "Drop in PDFs, YouTube lectures, or web articles. StudyMind extracts the substance and discards the noise.",
    points: ["Semantic PDF parsing", "Auto-transcribed video lectures"],
    size: "wide",
  },
  {
    icon: "🃏",
    title: "Instant Flashcards",
    body: "Every upload becomes spaced-repetition flashcards, tuned for what you're actually forgetting.",
    size: "tall",
    demo: "flashcard",
  },
  {
    icon: "🕸️",
    title: "Connected Knowledge",
    body: "StudyMind links related concepts across everything you've uploaded, so ideas stop living in isolated tabs.",
    size: "wide",
  },
];

const FLASHCARDS = [
  {
    q: "What is the time complexity of BST deletion?",
    a: "O(h) — O(log n) balanced, O(n) worst case.",
  },
  {
    q: "What replaces a node with two children in BST deletion?",
    a: "Its in-order successor: the smallest node in the right subtree.",
  },
  {
    q: "Define an AVL tree.",
    a: "A self-balancing BST where subtree heights differ by at most 1.",
  },
];

function useParticleCanvas(canvasRef) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let particles = [];
    let animationId;
    let width, height;

    const resize = () => {
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };

    class Particle {
      constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.size = Math.random() * 1.6 + 0.5;
        this.speedX = (Math.random() - 0.5) * 0.3;
        this.speedY = (Math.random() - 0.5) * 0.3;
        this.opacity = Math.random() * 0.4 + 0.15;
        this.color = Math.random() > 0.5 ? "124,58,237" : "6,182,212";
      }
      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x < 0 || this.x > width) this.speedX *= -1;
        if (this.y < 0 || this.y > height) this.speedY *= -1;
      }
      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${this.color},${this.opacity})`;
        ctx.fill();
      }
    }

    const init = () => {
      resize();
      particles = [];
      const count = Math.min(70, Math.floor((width * height) / 16000));
      for (let i = 0; i < count; i++) particles.push(new Particle());
    };

    const connect = () => {
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 110) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(124,58,237,${0.1 * (1 - dist / 110)})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }
    };

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      particles.forEach((p) => {
        p.update();
        p.draw();
      });
      connect();
      animationId = requestAnimationFrame(animate);
    };

    init();
    animate();
    window.addEventListener("resize", init);
    return () => {
      window.removeEventListener("resize", init);
      cancelAnimationFrame(animationId);
    };
  }, [canvasRef]);
}

function FlashcardDemo() {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const next = (e) => {
    e.stopPropagation();
    setFlipped(false);
    setTimeout(() => setIndex((i) => (i + 1) % FLASHCARDS.length), 150);
  };

  return (
    <div className="flashcard-demo">
      <div
        className={`flashcard ${flipped ? "flipped" : ""}`}
        onClick={() => setFlipped((f) => !f)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setFlipped((f) => !f)}
      >
        <div className="flashcard-face flashcard-front">
          <span className="flashcard-label">Question</span>
          <p>{FLASHCARDS[index].q}</p>
        </div>
        <div className="flashcard-face flashcard-back">
          <span className="flashcard-label">Answer</span>
          <p>{FLASHCARDS[index].a}</p>
        </div>
      </div>
      <div className="flashcard-controls">
        <span>{index + 1} / {FLASHCARDS.length}</span>
        <button onClick={next}>Next card →</button>
      </div>
    </div>
  );
}

export default function LandingPage({ onNavigate = () => {} }) {
  const canvasRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);
  useParticleCanvas(canvasRef);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <nav className={`navbar ${scrolled ? "scrolled" : ""}`}>
  <div className="logo">
    <span className="logo-icon">🧠</span>
    <span className="logo-text">StudyMind <span>AI</span></span>
  </div>
  <div className="nav-links">
    <a href="#features" onClick={(e) => {
      e.preventDefault();
      document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
    }}>Features</a>
    <a href="#" onClick={(e) => e.preventDefault()}>How it Works</a>
  </div>
  <div className="nav-actions">
    <ThemeToggle />
    <button className="btn-ghost" onClick={() => onNavigate("login")}>Log in</button>
    <button className="btn-cta" onClick={() => onNavigate("signup")}>Sign up</button>
  </div>
</nav>

      <section className="hero">
        <canvas ref={canvasRef} className="particle-canvas" />
        <div className="hero-content">
          <div className="hero-badge">
            <span className="dot" />
            Your notes, videos and articles — one workspace
          </div>
          <h1 className="hero-title">
            Learn smarter with your own <span className="highlight">AI study partner</span>
          </h1>
          <p className="hero-subtitle">
            Upload your material, ask questions grounded in what you actually studied,
            and turn it into flashcards and quizzes automatically.
          </p>
          <div className="hero-tags">
            <span className="tag">📄 PDFs</span>
            <span className="tag">▶️ Lecture videos</span>
            <span className="tag">🌐 Web articles</span>
          </div>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => onNavigate("signup")}>
              Get started free
            </button>
            <button className="btn-secondary" onClick={() => {
              document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
            }}>
              See how it works
            </button>
          </div>
        </div>
      </section>

      <section className="features" id="features">
        <div className="features-header">
          <h2>Everything you need to actually retain it</h2>
          <p>Stop losing material across a dozen tabs — StudyMind keeps it connected.</p>
        </div>
        <div className="bento-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className={`bento-card ${f.size}`}>
              <div className="bento-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
              {f.points && (
                <ul>
                  {f.points.map((p) => (
                    <li key={p}>✓ {p}</li>
                  ))}
                </ul>
              )}
              {f.demo === "flashcard" && <FlashcardDemo />}
            </div>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <div className="cta-card">
          <h2>Start turning your notes into knowledge</h2>
          <p>Free to start. No credit card required.</p>
          <button className="btn-primary" onClick={() => onNavigate("signup")}>
            Create your account
          </button>
        </div>
      </section>

      <footer className="footer">
        <div>
          <span className="logo-text">StudyMind <span>AI</span></span>
          <p>Your personal AI-powered learning workspace.</p>
        </div>
        <p className="footer-copy">© 2026 StudyMind AI</p>
      </footer>
    </div>
  );
}
