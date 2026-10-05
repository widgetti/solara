// feature "jquery": the real jQuery. Every 'jquery' import of the app bundle gets the stand-in of the core (../jquery),
// so this chunk imports jQuery by its file, and hands it to the stand-in. The page runs this chunk before the first
// view when the feature is on, and the jupyter-controls and output-widget chunks run after it (see ../features).
import jQuery from 'jquery/dist/jquery.js';
import Backbone from 'backbone';
import { setJQuery } from '../jquery';

setJQuery(jQuery);
// Backbone keeps what its 'jquery' import gave it (the stand-in) as Backbone.$, also window.Backbone.$: as before,
// that is jQuery itself
(Backbone as any).$ = jQuery;

export { jQuery };
