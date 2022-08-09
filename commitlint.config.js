module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["BEHAVIOR", "BREAK", "DOC", "DX", "ENH", "FEAT", "FIX", "MAINT"],
    ],
  },
};
