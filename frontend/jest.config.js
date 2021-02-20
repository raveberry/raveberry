module.exports = {
  'preset': 'ts-jest',
  'moduleNameMapper': {
    '^@src/(.*)$': [
      '<rootDir>/ts/$1',
    ],
  },
  'setupFilesAfterEnv': ['<rootDir>/jest-setup.ts'],
};
