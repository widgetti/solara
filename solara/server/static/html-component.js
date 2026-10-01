define('solara-html', ['@jupyter-widgets/base'], function (widgets) {
    'use strict';

    const BASE_URL = (window.solara && window.solara.rootPath || '').replace(/\/$/, '');
    const SAFE_PROPERTIES = {
        checked: 'checked',
        disabled: 'disabled',
        hidden: 'hidden',
        indeterminate: 'indeterminate',
        multiple: 'multiple',
        readonly: 'readOnly',
        required: 'required',
        selected: 'selected',
        textcontent: 'textContent',
        value: 'value',
    };
    const URL_ATTRIBUTES = new Set(['action', 'formaction', 'href', 'poster', 'src', 'xlink:href']);
    const SAFE_ATTRIBUTES = new Set([
        'action', 'alt', 'autocomplete', 'class', 'colspan', 'download', 'for', 'formaction',
        'height', 'href', 'id', 'max', 'min', 'name', 'placeholder', 'poster', 'rel',
        'role', 'rowspan', 'scope', 'src', 'step', 'tabindex', 'target', 'title', 'type',
        'value', 'width',
    ]);

    function assetUrl(filename) {
        return `${BASE_URL}/static/html-components/${encodeURIComponent(filename)}`;
    }

    function allowedUrl(value) {
        const text = String(value).trim();
        if (!text) return true;
        try {
            const parsed = new URL(text, document.baseURI);
            return ['http:', 'https:', 'mailto:', 'tel:', 'ftp:'].includes(parsed.protocol);
        } catch (_error) {
            return false;
        }
    }

    function checkTemplate(template) {
        const holder = document.createElement('template');
        holder.innerHTML = template;
        const elements = holder.content.querySelectorAll('*');
        for (const element of elements) {
            if (element.tagName.toLowerCase() === 'script') {
                throw new Error('HTML component template cannot contain <script> elements');
            }
            for (const attribute of element.attributes) {
                if (/^on/i.test(attribute.name)) {
                    throw new Error(`HTML component template cannot contain inline event attribute ${attribute.name}`);
                }
                const name = attribute.name.toLowerCase();
                // Resolve the documented public-asset spelling beside the extracted section.
                if (URL_ATTRIBUTES.has(name) && attribute.value.startsWith('../public/')) {
                    const base = `${window.location.origin}${BASE_URL}/static/html-components/`;
                    element.setAttribute(name, new URL(attribute.value, base).toString());
                }
                if (URL_ATTRIBUTES.has(name) && !allowedUrl(attribute.value)) {
                    throw new Error(`HTML component template contains an unsafe URL in ${name}`);
                }
            }
        }
        return holder;
    }

    class HTMLComponentModel extends widgets.DOMWidgetModel {
        defaults() {
            return Object.assign({}, super.defaults(), {
                _model_name: 'HTMLComponentModel',
                _view_name: 'HTMLComponentView',
                _model_module: 'solara-html',
                _view_module: 'solara-html',
                _model_module_version: '0.1.0',
                _view_module_version: '0.1.0',
                template: '',
                css_asset: '',
                script_asset: '',
                prop_names: [],
                event_names: [],
                children: null,
            });
        }
    }
    HTMLComponentModel.serializers = Object.assign({}, widgets.DOMWidgetModel.serializers, {
        children: { deserialize: widgets.unpack_models },
    });

    class HTMLComponentView extends widgets.DOMWidgetView {
        render() {
            this.el.classList.add('solara-html-component');
            this._childRecords = [];
            this._domCleanups = [];
            this._subscriptions = new Set();
            this._controllerCleanup = null;
            this._controllerGeneration = 0;
            this._isRemoved = false;
            this._templateSignature = null;
            this._shadow = this.el.shadowRoot || this.el.attachShadow({ mode: 'open' });
            this.listenTo(this.model, 'change', this._onModelChange);
            this.listenTo(this.model, 'change:children', this._reconcileChildren);
            this._installTemplate();
            this._reconcileChildren();
            return this;
        }

        _onModelChange() {
            if (this._isRemoved) return;
            const signature = [this.model.get('template'), this.model.get('css_asset'), this.model.get('script_asset')];
            if (!this._templateSignature || signature.some((value, index) => value !== this._templateSignature[index])) {
                this._installTemplate();
            } else {
                this._updateBindings();
            }
        }

        _disposeTemplate() {
            this._controllerGeneration += 1;
            if (typeof this._controllerCleanup === 'function') {
                try { this._controllerCleanup(); } catch (error) { console.error('HTML component cleanup failed', error); }
            }
            this._controllerCleanup = null;
            this._domCleanups.splice(0).forEach(cleanup => cleanup());
            for (const subscription of this._subscriptions) {
                this.model.off(`change:${subscription.name}`, subscription.listener, this);
            }
            this._subscriptions.clear();
        }

        _installTemplate() {
            this._disposeTemplate();
            const generation = this._controllerGeneration;
            this._templateSignature = [this.model.get('template'), this.model.get('css_asset'), this.model.get('script_asset')];
            const templateText = this.model.get('template') || '';
            try {
                const fragment = checkTemplate(templateText);
                this._shadow.replaceChildren();
                const cssAsset = this.model.get('css_asset');
                if (cssAsset) {
                    const link = document.createElement('link');
                    link.rel = 'stylesheet';
                    link.href = assetUrl(cssAsset);
                    this._shadow.appendChild(link);
                }
                this._shadow.appendChild(fragment.content.cloneNode(true));
                this._installBindings();
                this._updateBindings();
                this._loadController(generation);
            } catch (error) {
                console.error('Unable to render HTML component', error);
                this._shadow.replaceChildren(document.createTextNode(`HTML component error: ${error.message}`));
            }
        }

        _elements() {
            return Array.from(this._shadow.querySelectorAll('*'));
        }

        _installBindings() {
            const props = new Set(this.model.get('prop_names') || []);
            const events = new Set(this.model.get('event_names') || []);
            for (const element of this._elements()) {
                for (const attribute of Array.from(element.attributes)) {
                    const name = attribute.name.toLowerCase();
                    const value = attribute.value;
                    if (name === 'data-solara-text') {
                        this._assertProp(props, value);
                    } else if (name.startsWith('data-solara-attr-')) {
                        const target = name.slice('data-solara-attr-'.length);
                        if (
                            !(SAFE_ATTRIBUTES.has(target) || target.startsWith('aria-') || target.startsWith('data-')) ||
                            !/^[a-z][a-z0-9:_-]*$/.test(target) || /^on/i.test(target) ||
                            target === 'srcdoc' || target.startsWith('data-solara-')
                        ) {
                            throw new Error(`Unsafe HTML attribute binding: ${target}`);
                        }
                        this._assertProp(props, value);
                    } else if (name.startsWith('data-solara-prop-')) {
                        const target = name.slice('data-solara-prop-'.length);
                        if (!SAFE_PROPERTIES[target]) throw new Error(`Unsupported DOM property binding: ${target}`);
                        this._assertProp(props, value);
                    } else if (name === 'data-solara-model') {
                        this._assertProp(props, value);
                        this._bindModel(element, value);
                    } else if (name.startsWith('data-solara-event-')) {
                        const domEvent = name.slice('data-solara-event-'.length);
                        if (!/^[a-z][a-z0-9:-]*$/.test(domEvent)) throw new Error(`Invalid DOM event binding: ${domEvent}`);
                        if (!events.has(value)) throw new Error(`Undeclared Python event callback: ${value}`);
                        const listener = () => this.model.send({ type: 'event', name: value, data: null });
                        element.addEventListener(domEvent, listener);
                        this._domCleanups.push(() => element.removeEventListener(domEvent, listener));
                    }
                }
            }
        }

        _assertProp(props, name) {
            if (!props.has(name)) throw new Error(`Unknown HTML component prop: ${name}`);
        }

        _bindModel(element, propName) {
            const tag = element.tagName.toLowerCase();
            const type = tag === 'input' ? (element.getAttribute('type') || 'text').toLowerCase() : '';
            let eventName;
            if ((tag === 'input' && type === 'text') || tag === 'textarea') {
                eventName = 'input';
            } else if (tag === 'input' && type === 'checkbox') {
                eventName = 'change';
            } else if (tag === 'select' && !element.multiple) {
                eventName = 'change';
            } else {
                throw new Error('data-solara-model requires a text input, textarea, checkbox, or single select');
            }
            const listener = () => {
                const value = tag === 'input' && type === 'checkbox' ? element.checked : element.value;
                if (!Object.is(this.model.get(propName), value)) {
                    this.model.set(propName, value);
                    this.model.save_changes();
                }
            };
            element.addEventListener(eventName, listener);
            this._domCleanups.push(() => element.removeEventListener(eventName, listener));
        }

        _updateBindings() {
            for (const element of this._elements()) {
                for (const attribute of Array.from(element.attributes)) {
                    const name = attribute.name.toLowerCase();
                    const propName = attribute.value;
                    const value = this.model.get(propName);
                    if (name === 'data-solara-text') {
                        element.textContent = value == null ? '' : String(value);
                    } else if (name.startsWith('data-solara-attr-')) {
                        const target = name.slice('data-solara-attr-'.length);
                        if (value == null || value === false) {
                            element.removeAttribute(target);
                        } else if (URL_ATTRIBUTES.has(target) && !allowedUrl(value)) {
                            element.removeAttribute(target);
                        } else {
                            element.setAttribute(target, value === true ? '' : String(value));
                        }
                    } else if (name.startsWith('data-solara-prop-')) {
                        const property = SAFE_PROPERTIES[name.slice('data-solara-prop-'.length)];
                        if (property === 'textContent') {
                            element.textContent = value == null ? '' : String(value);
                        } else if (property === 'value') {
                            this._setValuePreservingSelection(element, value == null ? '' : String(value));
                        } else if (property) {
                            element[property] = Boolean(value);
                        }
                    } else if (name === 'data-solara-model') {
                        const type = element.tagName.toLowerCase() === 'input' ? (element.getAttribute('type') || 'text').toLowerCase() : '';
                        if (type === 'checkbox') {
                            element.checked = Boolean(value);
                        } else {
                            this._setValuePreservingSelection(element, value == null ? '' : String(value));
                        }
                    }
                }
            }
        }

        _setValuePreservingSelection(element, value) {
            if (element.value === value) return;
            const active = this._shadow.activeElement === element;
            let start = null, end = null, direction = null;
            if (active && typeof element.selectionStart === 'number') {
                start = element.selectionStart;
                end = element.selectionEnd;
                direction = element.selectionDirection;
            }
            element.value = value;
            if (start !== null) {
                const length = value.length;
                element.setSelectionRange(Math.min(start, length), Math.min(end, length), direction);
            }
        }

        async _loadController(generation) {
            const filename = this.model.get('script_asset');
            if (!filename) return;
            try {
                const controller = await import(assetUrl(filename));
                if (this._isRemoved || generation !== this._controllerGeneration) return;
                if (typeof controller.mount !== 'function') return;
                const active = () => !this._isRemoved && generation === this._controllerGeneration;
                const result = controller.mount({
                    root: this._shadow,
                    get: name => active() ? this.model.get(name) : undefined,
                    set: (name, value) => {
                        if (!active()) return;
                        if (!(this.model.get('prop_names') || []).includes(name)) throw new Error(`Unknown HTML component prop: ${name}`);
                        if (!Object.is(this.model.get(name), value)) {
                            this.model.set(name, value);
                            this.model.save_changes();
                        }
                    },
                    subscribe: (name, listener) => {
                        if (!active()) return () => {};
                        if (!(this.model.get('prop_names') || []).includes(name)) throw new Error(`Unknown HTML component prop: ${name}`);
                        const callback = () => listener(this.model.get(name));
                        this.model.on(`change:${name}`, callback, this);
                        const subscription = { name: name, listener: callback };
                        this._subscriptions.add(subscription);
                        return () => {
                            this.model.off(`change:${name}`, callback, this);
                            this._subscriptions.delete(subscription);
                        };
                    },
                    emit: (name, data) => {
                        if (!active()) return;
                        if (!(this.model.get('event_names') || []).includes(name)) throw new Error(`Undeclared Python event callback: ${name}`);
                        this.model.send({ type: 'event', name, data });
                    },
                });
                const cleanup = await result;
                if (typeof cleanup === 'function') {
                    if (this._isRemoved || generation !== this._controllerGeneration) cleanup();
                    else this._controllerCleanup = cleanup;
                }
            } catch (error) {
                if (!this._isRemoved && generation === this._controllerGeneration) {
                    console.error('HTML component controller failed', error);
                }
            }
        }

        _reconcileChildren() {
            const children = this.model.get('children');
            const models = children == null ? [] : (Array.isArray(children) ? children : [children]);
            const desiredModels = models.filter(model => model && typeof model.get === 'function');
            const previous = this._childRecords;
            const used = new Set();
            const next = desiredModels.map(model => {
                const index = previous.findIndex((record, i) => !used.has(i) && record.model === model);
                if (index !== -1) {
                    used.add(index);
                    return previous[index];
                }
                return { model: model, view: null, removed: false, container: null, promise: null };
            });
            previous.forEach((record, index) => {
                if (!used.has(index)) this._disposeChildRecord(record);
            });
            this._childRecords = next;

            let nextSibling = this.el.firstChild;
            for (const record of next) {
                record.removed = false;
                if (!record.container) {
                    record.container = document.createElement('div');
                    record.container.className = 'solara-html-child';
                    record.container.style.display = 'contents';
                }
                // Keep existing nodes in place when the child order is unchanged.
                if (record.container !== nextSibling) {
                    this.el.insertBefore(record.container, nextSibling);
                }
                nextSibling = record.container.nextSibling;
                if (!record.promise) {
                    record.promise = this.create_child_view(record.model).then(view => {
                        record.view = view;
                        if (record.removed || this._isRemoved || !this._childRecords.includes(record)) {
                            this._disposeChildRecord(record);
                        } else if (widgets.JupyterPhosphorWidget && view.pWidget) {
                            widgets.JupyterPhosphorWidget.attach(view.pWidget, record.container);
                        } else {
                            record.container.appendChild(view.el);
                        }
                        return view;
                    }).catch(error => console.error('Unable to create HTML component child view', error));
                }
            }
        }

        _disposeChildRecord(record) {
            record.removed = true;
            if (record.view) {
                if (record.view.pWidget && typeof record.view.pWidget.dispose === 'function') {
                    record.view.pWidget.dispose();
                } else {
                    record.view.remove();
                }
                record.view = null;
            }
            if (record.container && record.container.parentNode) {
                record.container.parentNode.removeChild(record.container);
            }
        }

        remove() {
            this._isRemoved = true;
            this.stopListening();
            this._disposeTemplate();
            this._childRecords.splice(0).forEach(record => this._disposeChildRecord(record));
            return super.remove();
        }
    }

    return { HTMLComponentModel: HTMLComponentModel, HTMLComponentView: HTMLComponentView };
});
