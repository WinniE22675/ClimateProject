/** @type {import('tailwindcss').Config} */
export default {
  // Specify the paths to all of your template files
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // We will add custom colors here later if needed to match Bootstrap exactly
      fontFamily: {
        sans: ['Inter', 'Noto Sans Thai', 'sans-serif'],
        // sans: ['Poppins', 'Prompt', 'sans-serif'],
      },
      colors: {
        'climate-primary': '#0462b4',
      }
    },
  },
  plugins: [],
}