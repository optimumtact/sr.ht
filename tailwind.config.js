/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Open Sans", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#fff7f5",
          100: "#ffe5df",
          500: "#d9230f",
          600: "#bf1f0d",
        },
        slate: {
          25: "#fbfbfc",
        },
      },
    },
  },
};
