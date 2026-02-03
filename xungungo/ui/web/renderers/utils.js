// utils.js
// Utilidades compartidas para el sistema de rendering

export const DEBUG = window.XUNGUNGO_DEBUG === true;

export const log = (...args) => {
  if (DEBUG) console.log(...args);
};

export const warn = (...args) => {
  if (DEBUG) console.warn(...args);
};
