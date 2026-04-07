/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        saffron: { DEFAULT: "#E8930A", light: "#FFF3E0", dark: "#C47A08" },
        navy: { DEFAULT: "#1B2A4A", light: "#2A3D5E" },
        gold: { DEFAULT: "#F5C563" },
      },
    },
  },
  plugins: [],
}
