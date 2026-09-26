import { createContext, useContext, useState, useEffect } from "react";

const ThemeContext = createContext();

export const COLOR_THEMES = [
  { id: "violet", label: "Violet", caption: "Purple + blue glow", swatch: "linear-gradient(135deg, #7c3aed, #2563eb)" },
  { id: "ocean", label: "Ocean", caption: "Sky blue + cyan", swatch: "linear-gradient(135deg, #0ea5e9, #2563eb)" },
  { id: "emerald", label: "Emerald", caption: "Green + teal", swatch: "linear-gradient(135deg, #10b981, #0d9488)" },
  { id: "rose", label: "Rose", caption: "Pink + crimson", swatch: "linear-gradient(135deg, #f43f5e, #e11d48)" },
  { id: "amber", label: "Amber", caption: "Gold + orange", swatch: "linear-gradient(135deg, #f59e0b, #ea580c)" },
];

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("studymind_theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch {}
    return "dark";
  });

  const [colorTheme, setColorTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("studymind_color_theme");
      if (saved && COLOR_THEMES.some((c) => c.id === saved)) return saved;
    } catch {}
    return "violet";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("studymind_theme", theme);
    } catch {}
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute("data-accent", colorTheme);
    try {
      localStorage.setItem("studymind_color_theme", colorTheme);
    } catch {}
  }, [colorTheme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const isDark = theme === "dark";

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark, colorTheme, setColorTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}