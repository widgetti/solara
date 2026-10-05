// The module that every 'jquery' import of the app bundle gets (the "jquery$" alias in the webpack configs of the
// apps): the stand-in $ of ./jquery. It is CommonJS on purpose, as the real jQuery is, so that module.exports is the
// $ function itself: Backbone and jQuery UI (AMD dependencies) get the function, not an ES module namespace.
// The file has no import or export, so TypeScript leaves this line as it is.
// @ts-ignore: module and require are CommonJS, which webpack provides
module.exports = require('./jquery').default;
