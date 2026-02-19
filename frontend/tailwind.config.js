/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
            colors: {
                sky: {
                    950: '#0a1628',
                    900: '#0d1f3c',
                    850: '#0f2647',
                    800: '#133060',
                },
                accent: {
                    blue: '#3b82f6',
                    cyan: '#06b6d4',
                    green: '#10b981',
                    amber: '#f59e0b',
                    red: '#ef4444',
                    orange: '#f97316',
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-in-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'pulse-slow': 'pulse 2s infinite',
                'typing': 'typing 1.5s infinite',
            },
            keyframes: {
                fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
                slideUp: { from: { transform: 'translateY(10px)', opacity: 0 }, to: { transform: 'translateY(0)', opacity: 1 } },
                typing: {
                    '0%, 60%, 100%': { transform: 'translateY(0)' },
                    '30%': { transform: 'translateY(-6px)' },
                },
            },
        },
    },
    plugins: [],
}
