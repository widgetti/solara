"use strict";
/***************************************************************************
 * Copyright (c) 2018, Voilà contributors                                   *
 * Copyright (c) 2018, QuantStack                                           *
 *                                                                          *
 * Distributed under the terms of the BSD 3-Clause License.                 *
 *                                                                          *
 * The full license is in the file LICENSE, distributed with this software. *
 ****************************************************************************/
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.shutdownKernel = exports.connectKernel = void 0;
const coreutils_1 = require("@jupyterlab/coreutils");
const services_1 = require("@jupyterlab/services");
const default_1 = require("@jupyterlab/services/lib/kernel/default");
const KernelMessage = __importStar(require("@jupyterlab/services/lib/kernel/messages"));
const SOLARA_KERNEL_TERMINATED_MSG_TYPE = 'solara_kernel_terminated';
function installSolaraKernelMessageLogging(kernel) {
    kernel.iopubMessage.connect((_, msg) => {
        if (msg.header.msg_type !== SOLARA_KERNEL_TERMINATED_MSG_TYPE) {
            return;
        }
        console.error('Solara kernel terminated:', msg.content);
        if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
            window.dispatchEvent(new CustomEvent('solara.kernelTerminated', {
                detail: msg.content,
            }));
        }
    });
}
function connectKernel(baseUrl, kernelId, options) {
    return __awaiter(this, void 0, void 0, function* () {
        baseUrl = baseUrl !== null && baseUrl !== void 0 ? baseUrl : coreutils_1.PageConfig.getBaseUrl();
        kernelId = kernelId !== null && kernelId !== void 0 ? kernelId : coreutils_1.PageConfig.getOption('kernelId');
        const serverSettings = services_1.ServerConnection.makeSettings(Object.assign({ baseUrl }, options));
        // const model = await KernelAPI.getKernelModel(kernelId, serverSettings);
        // if (!model) {
        //   return;
        // }
        const model = { 'id': kernelId, 'name': 'solara-name' };
        const kernel = new default_1.KernelConnection({ model, serverSettings });
        installSolaraKernelMessageLogging(kernel);
        return kernel;
    });
}
exports.connectKernel = connectKernel;
function shutdownKernel(kernel) {
    return __awaiter(this, void 0, void 0, function* () {
        // we cannot use this API since it uses the REST api
        // while we want to use the current websocket since this makes
        // sure the message gets delivered to the node/process where the
        // kernel is running
        // await kernel.shutdown();
        // so we use https://jupyter-protocol.readthedocs.io/en/latest/messaging.html#kernel-shutdown
        // @ts-ignore
        const msg = KernelMessage.createMessage({
            // @ts-ignore
            msgType: 'shutdown_request', channel: 'control', username: kernel._username, session: kernel._clientId, content: {
                // @ts-ignore
                'restart': false, // final shutdown, not a restart
            }
        });
        return yield kernel.sendControlMessage(msg);
    });
}
exports.shutdownKernel = shutdownKernel;
//# sourceMappingURL=kernel.js.map
