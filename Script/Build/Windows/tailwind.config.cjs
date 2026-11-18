const path = require('path');
const root = path.resolve(__dirname, '../../..');
module.exports = {
  content: [
    path.join(root, 'Code/GptSov_Front/index.html'),
    path.join(root, 'Code/GptSov_Front/App.tsx'),
    path.join(root, 'Code/GptSov_Front/Src/**/*.{ts,tsx}'),
  ],
  theme: { extend: {} },
  plugins: [],
};
