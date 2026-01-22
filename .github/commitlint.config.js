// Commitlint Configuration
// Enforces conventional commit message format

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Type must be one of the following
    'type-enum': [
      2,
      'always',
      [
        'feat',     // New feature
        'fix',      // Bug fix
        'docs',     // Documentation only
        'style',    // Code style (formatting, semicolons, etc.)
        'refactor', // Code refactoring
        'perf',     // Performance improvement
        'test',     // Adding/updating tests
        'build',    // Build system or dependencies
        'ci',       // CI/CD configuration
        'chore',    // Other changes (tooling, etc.)
        'revert',   // Revert previous commit
      ],
    ],
    // Type is required and must be lowercase
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
    
    // Subject requirements
    'subject-case': [2, 'always', 'lower-case'],
    'subject-empty': [2, 'never'],
    'subject-max-length': [2, 'always', 100],
    
    // Header requirements
    'header-max-length': [2, 'always', 100],
    
    // Body requirements
    'body-max-line-length': [2, 'always', 200],
    
    // Footer requirements
    'footer-max-line-length': [2, 'always', 200],
  },
  helpUrl: 'https://www.conventionalcommits.org/',
};
