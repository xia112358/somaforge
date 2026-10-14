var gd=Object.defineProperty;var _d=(i,t,e)=>t in i?gd(i,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):i[t]=e;var se=(i,t,e)=>_d(i,typeof t!="symbol"?t+"":t,e);(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))n(s);new MutationObserver(s=>{for(const r of s)if(r.type==="childList")for(const a of r.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&n(a)}).observe(document,{childList:!0,subtree:!0});function e(s){const r={};return s.integrity&&(r.integrity=s.integrity),s.referrerPolicy&&(r.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?r.credentials="include":s.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function n(s){if(s.ep)return;s.ep=!0;const r=e(s);fetch(s.href,r)}})();/**
 * @license
 * Copyright 2010-2024 Three.js Authors
 * SPDX-License-Identifier: MIT
 */const Uc="170",_s={ROTATE:0,DOLLY:1,PAN:2},ms={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},vd=0,al=1,xd=2,$h=1,yd=2,ni=3,ai=0,dn=1,un=2,wi=0,vs=1,cl=2,ll=3,hl=4,Md=5,Hi=100,Sd=101,bd=102,Ed=103,wd=104,Td=200,Ad=201,Cd=202,Rd=203,Va=204,Ha=205,Pd=206,Ld=207,Nd=208,Dd=209,Id=210,Ud=211,Fd=212,Od=213,kd=214,Ga=0,Wa=1,Xa=2,ws=3,qa=4,ja=5,Ya=6,$a=7,Uo=0,Bd=1,zd=2,Ti=0,Vd=1,Hd=2,Gd=3,Kh=4,Wd=5,Xd=6,qd=7,ul="attached",jd="detached",Jh=300,Ts=301,As=302,Ka=303,Ja=304,Fo=306,Wi=1e3,On=1001,Za=1002,vn=1003,Yd=1004,Rr=1005,_n=1006,Jo=1007,si=1008,ci=1009,Zh=1010,Qh=1011,cr=1012,Fc=1013,Xi=1014,Wn=1015,gr=1016,Oc=1017,kc=1018,Cs=1020,tu=35902,eu=1021,nu=1022,wn=1023,iu=1024,su=1025,xs=1026,Rs=1027,ru=1028,Bc=1029,ou=1030,zc=1031,Vc=1033,ho=33776,uo=33777,fo=33778,po=33779,Qa=35840,tc=35841,ec=35842,nc=35843,ic=36196,sc=37492,rc=37496,oc=37808,ac=37809,cc=37810,lc=37811,hc=37812,uc=37813,dc=37814,fc=37815,pc=37816,mc=37817,gc=37818,_c=37819,vc=37820,xc=37821,mo=36492,yc=36494,Mc=36495,au=36283,Sc=36284,bc=36285,Ec=36286,xo=2300,wc=2301,Zo=2302,dl=2400,fl=2401,pl=2402,$d=2500,Kd=3200,Jd=3201,Oo=0,Zd=1,Ei="",Le="srgb",Us="srgb-linear",ko="linear",Ee="srgb",Qi=7680,ml=519,Qd=512,tf=513,ef=514,cu=515,nf=516,sf=517,rf=518,of=519,gl=35044,_l="300 es",ri=2e3,yo=2001;class $i{addEventListener(t,e){this._listeners===void 0&&(this._listeners={});const n=this._listeners;n[t]===void 0&&(n[t]=[]),n[t].indexOf(e)===-1&&n[t].push(e)}hasEventListener(t,e){if(this._listeners===void 0)return!1;const n=this._listeners;return n[t]!==void 0&&n[t].indexOf(e)!==-1}removeEventListener(t,e){if(this._listeners===void 0)return;const s=this._listeners[t];if(s!==void 0){const r=s.indexOf(e);r!==-1&&s.splice(r,1)}}dispatchEvent(t){if(this._listeners===void 0)return;const n=this._listeners[t.type];if(n!==void 0){t.target=this;const s=n.slice(0);for(let r=0,a=s.length;r<a;r++)s[r].call(this,t);t.target=null}}}const $e=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"];let vl=1234567;const ir=Math.PI/180,Ps=180/Math.PI;function Li(){const i=Math.random()*4294967295|0,t=Math.random()*4294967295|0,e=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return($e[i&255]+$e[i>>8&255]+$e[i>>16&255]+$e[i>>24&255]+"-"+$e[t&255]+$e[t>>8&255]+"-"+$e[t>>16&15|64]+$e[t>>24&255]+"-"+$e[e&63|128]+$e[e>>8&255]+"-"+$e[e>>16&255]+$e[e>>24&255]+$e[n&255]+$e[n>>8&255]+$e[n>>16&255]+$e[n>>24&255]).toLowerCase()}function qe(i,t,e){return Math.max(t,Math.min(e,i))}function Hc(i,t){return(i%t+t)%t}function af(i,t,e,n,s){return n+(i-t)*(s-n)/(e-t)}function cf(i,t,e){return i!==t?(e-i)/(t-i):0}function sr(i,t,e){return(1-e)*i+e*t}function lf(i,t,e,n){return sr(i,t,1-Math.exp(-e*n))}function hf(i,t=1){return t-Math.abs(Hc(i,t*2)-t)}function uf(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*(3-2*i))}function df(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*i*(i*(i*6-15)+10))}function ff(i,t){return i+Math.floor(Math.random()*(t-i+1))}function pf(i,t){return i+Math.random()*(t-i)}function mf(i){return i*(.5-Math.random())}function gf(i){i!==void 0&&(vl=i);let t=vl+=1831565813;return t=Math.imul(t^t>>>15,t|1),t^=t+Math.imul(t^t>>>7,t|61),((t^t>>>14)>>>0)/4294967296}function _f(i){return i*ir}function vf(i){return i*Ps}function xf(i){return(i&i-1)===0&&i!==0}function yf(i){return Math.pow(2,Math.ceil(Math.log(i)/Math.LN2))}function Mf(i){return Math.pow(2,Math.floor(Math.log(i)/Math.LN2))}function Sf(i,t,e,n,s){const r=Math.cos,a=Math.sin,o=r(e/2),c=a(e/2),l=r((t+n)/2),h=a((t+n)/2),u=r((t-n)/2),f=a((t-n)/2),p=r((n-t)/2),g=a((n-t)/2);switch(s){case"XYX":i.set(o*h,c*u,c*f,o*l);break;case"YZY":i.set(c*f,o*h,c*u,o*l);break;case"ZXZ":i.set(c*u,c*f,o*h,o*l);break;case"XZX":i.set(o*h,c*g,c*p,o*l);break;case"YXY":i.set(c*p,o*h,c*g,o*l);break;case"ZYZ":i.set(c*g,c*p,o*h,o*l);break;default:console.warn("THREE.MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+s)}}function fs(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return i/4294967295;case Uint16Array:return i/65535;case Uint8Array:return i/255;case Int32Array:return Math.max(i/2147483647,-1);case Int16Array:return Math.max(i/32767,-1);case Int8Array:return Math.max(i/127,-1);default:throw new Error("Invalid component type.")}}function tn(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return Math.round(i*4294967295);case Uint16Array:return Math.round(i*65535);case Uint8Array:return Math.round(i*255);case Int32Array:return Math.round(i*2147483647);case Int16Array:return Math.round(i*32767);case Int8Array:return Math.round(i*127);default:throw new Error("Invalid component type.")}}const ps={DEG2RAD:ir,RAD2DEG:Ps,generateUUID:Li,clamp:qe,euclideanModulo:Hc,mapLinear:af,inverseLerp:cf,lerp:sr,damp:lf,pingpong:hf,smoothstep:uf,smootherstep:df,randInt:ff,randFloat:pf,randFloatSpread:mf,seededRandom:gf,degToRad:_f,radToDeg:vf,isPowerOfTwo:xf,ceilPowerOfTwo:yf,floorPowerOfTwo:Mf,setQuaternionFromProperEuler:Sf,normalize:tn,denormalize:fs};class At{constructor(t=0,e=0){At.prototype.isVector2=!0,this.x=t,this.y=e}get width(){return this.x}set width(t){this.x=t}get height(){return this.y}set height(t){this.y=t}set(t,e){return this.x=t,this.y=e,this}setScalar(t){return this.x=t,this.y=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y)}copy(t){return this.x=t.x,this.y=t.y,this}add(t){return this.x+=t.x,this.y+=t.y,this}addScalar(t){return this.x+=t,this.y+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this}subScalar(t){return this.x-=t,this.y-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this}multiply(t){return this.x*=t.x,this.y*=t.y,this}multiplyScalar(t){return this.x*=t,this.y*=t,this}divide(t){return this.x/=t.x,this.y/=t.y,this}divideScalar(t){return this.multiplyScalar(1/t)}applyMatrix3(t){const e=this.x,n=this.y,s=t.elements;return this.x=s[0]*e+s[3]*n+s[6],this.y=s[1]*e+s[4]*n+s[7],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(t){return this.x*t.x+this.y*t.y}cross(t){return this.x*t.y-this.y*t.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(qe(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y;return e*e+n*n}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this}equals(t){return t.x===this.x&&t.y===this.y}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this}rotateAround(t,e){const n=Math.cos(e),s=Math.sin(e),r=this.x-t.x,a=this.y-t.y;return this.x=r*n-a*s+t.x,this.y=r*s+a*n+t.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class re{constructor(t,e,n,s,r,a,o,c,l){re.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],t!==void 0&&this.set(t,e,n,s,r,a,o,c,l)}set(t,e,n,s,r,a,o,c,l){const h=this.elements;return h[0]=t,h[1]=s,h[2]=o,h[3]=e,h[4]=r,h[5]=c,h[6]=n,h[7]=a,h[8]=l,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],this}extractBasis(t,e,n){return t.setFromMatrix3Column(this,0),e.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(t){const e=t.elements;return this.set(e[0],e[4],e[8],e[1],e[5],e[9],e[2],e[6],e[10]),this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,s=e.elements,r=this.elements,a=n[0],o=n[3],c=n[6],l=n[1],h=n[4],u=n[7],f=n[2],p=n[5],g=n[8],_=s[0],m=s[3],d=s[6],w=s[1],T=s[4],M=s[7],F=s[2],P=s[5],N=s[8];return r[0]=a*_+o*w+c*F,r[3]=a*m+o*T+c*P,r[6]=a*d+o*M+c*N,r[1]=l*_+h*w+u*F,r[4]=l*m+h*T+u*P,r[7]=l*d+h*M+u*N,r[2]=f*_+p*w+g*F,r[5]=f*m+p*T+g*P,r[8]=f*d+p*M+g*N,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[3]*=t,e[6]*=t,e[1]*=t,e[4]*=t,e[7]*=t,e[2]*=t,e[5]*=t,e[8]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8];return e*a*h-e*o*l-n*r*h+n*o*c+s*r*l-s*a*c}invert(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8],u=h*a-o*l,f=o*c-h*r,p=l*r-a*c,g=e*u+n*f+s*p;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);const _=1/g;return t[0]=u*_,t[1]=(s*l-h*n)*_,t[2]=(o*n-s*a)*_,t[3]=f*_,t[4]=(h*e-s*c)*_,t[5]=(s*r-o*e)*_,t[6]=p*_,t[7]=(n*c-l*e)*_,t[8]=(a*e-n*r)*_,this}transpose(){let t;const e=this.elements;return t=e[1],e[1]=e[3],e[3]=t,t=e[2],e[2]=e[6],e[6]=t,t=e[5],e[5]=e[7],e[7]=t,this}getNormalMatrix(t){return this.setFromMatrix4(t).invert().transpose()}transposeIntoArray(t){const e=this.elements;return t[0]=e[0],t[1]=e[3],t[2]=e[6],t[3]=e[1],t[4]=e[4],t[5]=e[7],t[6]=e[2],t[7]=e[5],t[8]=e[8],this}setUvTransform(t,e,n,s,r,a,o){const c=Math.cos(r),l=Math.sin(r);return this.set(n*c,n*l,-n*(c*a+l*o)+a+t,-s*l,s*c,-s*(-l*a+c*o)+o+e,0,0,1),this}scale(t,e){return this.premultiply(Qo.makeScale(t,e)),this}rotate(t){return this.premultiply(Qo.makeRotation(-t)),this}translate(t,e){return this.premultiply(Qo.makeTranslation(t,e)),this}makeTranslation(t,e){return t.isVector2?this.set(1,0,t.x,0,1,t.y,0,0,1):this.set(1,0,t,0,1,e,0,0,1),this}makeRotation(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,n,e,0,0,0,1),this}makeScale(t,e){return this.set(t,0,0,0,e,0,0,0,1),this}equals(t){const e=this.elements,n=t.elements;for(let s=0;s<9;s++)if(e[s]!==n[s])return!1;return!0}fromArray(t,e=0){for(let n=0;n<9;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t}clone(){return new this.constructor().fromArray(this.elements)}}const Qo=new re;function lu(i){for(let t=i.length-1;t>=0;--t)if(i[t]>=65535)return!0;return!1}function lr(i){return document.createElementNS("http://www.w3.org/1999/xhtml",i)}function bf(){const i=lr("canvas");return i.style.display="block",i}const xl={};function Zs(i){i in xl||(xl[i]=!0,console.warn(i))}function Ef(i,t,e){return new Promise(function(n,s){function r(){switch(i.clientWaitSync(t,i.SYNC_FLUSH_COMMANDS_BIT,0)){case i.WAIT_FAILED:s();break;case i.TIMEOUT_EXPIRED:setTimeout(r,e);break;default:n()}}setTimeout(r,e)})}function wf(i){const t=i.elements;t[2]=.5*t[2]+.5*t[3],t[6]=.5*t[6]+.5*t[7],t[10]=.5*t[10]+.5*t[11],t[14]=.5*t[14]+.5*t[15]}function Tf(i){const t=i.elements;t[11]===-1?(t[10]=-t[10]-1,t[14]=-t[14]):(t[10]=-t[10],t[14]=-t[14]+1)}const le={enabled:!0,workingColorSpace:Us,spaces:{},convert:function(i,t,e){return this.enabled===!1||t===e||!t||!e||(this.spaces[t].transfer===Ee&&(i.r=oi(i.r),i.g=oi(i.g),i.b=oi(i.b)),this.spaces[t].primaries!==this.spaces[e].primaries&&(i.applyMatrix3(this.spaces[t].toXYZ),i.applyMatrix3(this.spaces[e].fromXYZ)),this.spaces[e].transfer===Ee&&(i.r=ys(i.r),i.g=ys(i.g),i.b=ys(i.b))),i},fromWorkingColorSpace:function(i,t){return this.convert(i,this.workingColorSpace,t)},toWorkingColorSpace:function(i,t){return this.convert(i,t,this.workingColorSpace)},getPrimaries:function(i){return this.spaces[i].primaries},getTransfer:function(i){return i===Ei?ko:this.spaces[i].transfer},getLuminanceCoefficients:function(i,t=this.workingColorSpace){return i.fromArray(this.spaces[t].luminanceCoefficients)},define:function(i){Object.assign(this.spaces,i)},_getMatrix:function(i,t,e){return i.copy(this.spaces[t].toXYZ).multiply(this.spaces[e].fromXYZ)},_getDrawingBufferColorSpace:function(i){return this.spaces[i].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(i=this.workingColorSpace){return this.spaces[i].workingColorSpaceConfig.unpackColorSpace}};function oi(i){return i<.04045?i*.0773993808:Math.pow(i*.9478672986+.0521327014,2.4)}function ys(i){return i<.0031308?i*12.92:1.055*Math.pow(i,.41666)-.055}const yl=[.64,.33,.3,.6,.15,.06],Ml=[.2126,.7152,.0722],Sl=[.3127,.329],bl=new re().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),El=new re().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);le.define({[Us]:{primaries:yl,whitePoint:Sl,transfer:ko,toXYZ:bl,fromXYZ:El,luminanceCoefficients:Ml,workingColorSpaceConfig:{unpackColorSpace:Le},outputColorSpaceConfig:{drawingBufferColorSpace:Le}},[Le]:{primaries:yl,whitePoint:Sl,transfer:Ee,toXYZ:bl,fromXYZ:El,luminanceCoefficients:Ml,outputColorSpaceConfig:{drawingBufferColorSpace:Le}}});let ts;class Af{static getDataURL(t){if(/^data:/i.test(t.src)||typeof HTMLCanvasElement>"u")return t.src;let e;if(t instanceof HTMLCanvasElement)e=t;else{ts===void 0&&(ts=lr("canvas")),ts.width=t.width,ts.height=t.height;const n=ts.getContext("2d");t instanceof ImageData?n.putImageData(t,0,0):n.drawImage(t,0,0,t.width,t.height),e=ts}return e.width>2048||e.height>2048?(console.warn("THREE.ImageUtils.getDataURL: Image converted to jpg for performance reasons",t),e.toDataURL("image/jpeg",.6)):e.toDataURL("image/png")}static sRGBToLinear(t){if(typeof HTMLImageElement<"u"&&t instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&t instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&t instanceof ImageBitmap){const e=lr("canvas");e.width=t.width,e.height=t.height;const n=e.getContext("2d");n.drawImage(t,0,0,t.width,t.height);const s=n.getImageData(0,0,t.width,t.height),r=s.data;for(let a=0;a<r.length;a++)r[a]=oi(r[a]/255)*255;return n.putImageData(s,0,0),e}else if(t.data){const e=t.data.slice(0);for(let n=0;n<e.length;n++)e instanceof Uint8Array||e instanceof Uint8ClampedArray?e[n]=Math.floor(oi(e[n]/255)*255):e[n]=oi(e[n]);return{data:e,width:t.width,height:t.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),t}}let Cf=0;class hu{constructor(t=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Cf++}),this.uuid=Li(),this.data=t,this.dataReady=!0,this.version=0}set needsUpdate(t){t===!0&&this.version++}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.images[this.uuid]!==void 0)return t.images[this.uuid];const n={uuid:this.uuid,url:""},s=this.data;if(s!==null){let r;if(Array.isArray(s)){r=[];for(let a=0,o=s.length;a<o;a++)s[a].isDataTexture?r.push(ta(s[a].image)):r.push(ta(s[a]))}else r=ta(s);n.url=r}return e||(t.images[this.uuid]=n),n}}function ta(i){return typeof HTMLImageElement<"u"&&i instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&i instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&i instanceof ImageBitmap?Af.getDataURL(i):i.data?{data:Array.from(i.data),width:i.width,height:i.height,type:i.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}let Rf=0;class Ye extends $i{constructor(t=Ye.DEFAULT_IMAGE,e=Ye.DEFAULT_MAPPING,n=On,s=On,r=_n,a=si,o=wn,c=ci,l=Ye.DEFAULT_ANISOTROPY,h=Ei){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:Rf++}),this.uuid=Li(),this.name="",this.source=new hu(t),this.mipmaps=[],this.mapping=e,this.channel=0,this.wrapS=n,this.wrapT=s,this.magFilter=r,this.minFilter=a,this.anisotropy=l,this.format=o,this.internalFormat=null,this.type=c,this.offset=new At(0,0),this.repeat=new At(1,1),this.center=new At(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new re,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=h,this.userData={},this.version=0,this.onUpdate=null,this.isRenderTargetTexture=!1,this.pmremVersion=0}get image(){return this.source.data}set image(t=null){this.source.data=t}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}clone(){return new this.constructor().copy(this)}copy(t){return this.name=t.name,this.source=t.source,this.mipmaps=t.mipmaps.slice(0),this.mapping=t.mapping,this.channel=t.channel,this.wrapS=t.wrapS,this.wrapT=t.wrapT,this.magFilter=t.magFilter,this.minFilter=t.minFilter,this.anisotropy=t.anisotropy,this.format=t.format,this.internalFormat=t.internalFormat,this.type=t.type,this.offset.copy(t.offset),this.repeat.copy(t.repeat),this.center.copy(t.center),this.rotation=t.rotation,this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrix.copy(t.matrix),this.generateMipmaps=t.generateMipmaps,this.premultiplyAlpha=t.premultiplyAlpha,this.flipY=t.flipY,this.unpackAlignment=t.unpackAlignment,this.colorSpace=t.colorSpace,this.userData=JSON.parse(JSON.stringify(t.userData)),this.needsUpdate=!0,this}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.textures[this.uuid]!==void 0)return t.textures[this.uuid];const n={metadata:{version:4.6,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(t).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),e||(t.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(t){if(this.mapping!==Jh)return t;if(t.applyMatrix3(this.matrix),t.x<0||t.x>1)switch(this.wrapS){case Wi:t.x=t.x-Math.floor(t.x);break;case On:t.x=t.x<0?0:1;break;case Za:Math.abs(Math.floor(t.x)%2)===1?t.x=Math.ceil(t.x)-t.x:t.x=t.x-Math.floor(t.x);break}if(t.y<0||t.y>1)switch(this.wrapT){case Wi:t.y=t.y-Math.floor(t.y);break;case On:t.y=t.y<0?0:1;break;case Za:Math.abs(Math.floor(t.y)%2)===1?t.y=Math.ceil(t.y)-t.y:t.y=t.y-Math.floor(t.y);break}return this.flipY&&(t.y=1-t.y),t}set needsUpdate(t){t===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(t){t===!0&&this.pmremVersion++}}Ye.DEFAULT_IMAGE=null;Ye.DEFAULT_MAPPING=Jh;Ye.DEFAULT_ANISOTROPY=1;class xe{constructor(t=0,e=0,n=0,s=1){xe.prototype.isVector4=!0,this.x=t,this.y=e,this.z=n,this.w=s}get width(){return this.z}set width(t){this.z=t}get height(){return this.w}set height(t){this.w=t}set(t,e,n,s){return this.x=t,this.y=e,this.z=n,this.w=s,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this.w=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setW(t){return this.w=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;case 3:this.w=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this.w=t.w!==void 0?t.w:1,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this.w+=t.w,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this.w+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this.w=t.w+e.w,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this.w+=t.w*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this.w-=t.w,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this.w-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this.w=t.w-e.w,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this.w*=t.w,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this.w*=t,this}applyMatrix4(t){const e=this.x,n=this.y,s=this.z,r=this.w,a=t.elements;return this.x=a[0]*e+a[4]*n+a[8]*s+a[12]*r,this.y=a[1]*e+a[5]*n+a[9]*s+a[13]*r,this.z=a[2]*e+a[6]*n+a[10]*s+a[14]*r,this.w=a[3]*e+a[7]*n+a[11]*s+a[15]*r,this}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this.w/=t.w,this}divideScalar(t){return this.multiplyScalar(1/t)}setAxisAngleFromQuaternion(t){this.w=2*Math.acos(t.w);const e=Math.sqrt(1-t.w*t.w);return e<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=t.x/e,this.y=t.y/e,this.z=t.z/e),this}setAxisAngleFromRotationMatrix(t){let e,n,s,r;const c=t.elements,l=c[0],h=c[4],u=c[8],f=c[1],p=c[5],g=c[9],_=c[2],m=c[6],d=c[10];if(Math.abs(h-f)<.01&&Math.abs(u-_)<.01&&Math.abs(g-m)<.01){if(Math.abs(h+f)<.1&&Math.abs(u+_)<.1&&Math.abs(g+m)<.1&&Math.abs(l+p+d-3)<.1)return this.set(1,0,0,0),this;e=Math.PI;const T=(l+1)/2,M=(p+1)/2,F=(d+1)/2,P=(h+f)/4,N=(u+_)/4,D=(g+m)/4;return T>M&&T>F?T<.01?(n=0,s=.707106781,r=.707106781):(n=Math.sqrt(T),s=P/n,r=N/n):M>F?M<.01?(n=.707106781,s=0,r=.707106781):(s=Math.sqrt(M),n=P/s,r=D/s):F<.01?(n=.707106781,s=.707106781,r=0):(r=Math.sqrt(F),n=N/r,s=D/r),this.set(n,s,r,e),this}let w=Math.sqrt((m-g)*(m-g)+(u-_)*(u-_)+(f-h)*(f-h));return Math.abs(w)<.001&&(w=1),this.x=(m-g)/w,this.y=(u-_)/w,this.z=(f-h)/w,this.w=Math.acos((l+p+d-1)/2),this}setFromMatrixPosition(t){const e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this.w=e[15],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this.w=Math.min(this.w,t.w),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this.w=Math.max(this.w,t.w),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this.w=Math.max(t.w,Math.min(e.w,this.w)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this.w=Math.max(t,Math.min(e,this.w)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z+this.w*t.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this.w+=(t.w-this.w)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this.w=t.w+(e.w-t.w)*n,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z&&t.w===this.w}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this.w=t[e+3],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t[e+3]=this.w,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this.w=t.getW(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class Pf extends $i{constructor(t=1,e=1,n={}){super(),this.isRenderTarget=!0,this.width=t,this.height=e,this.depth=1,this.scissor=new xe(0,0,t,e),this.scissorTest=!1,this.viewport=new xe(0,0,t,e);const s={width:t,height:e,depth:1};n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:_n,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1},n);const r=new Ye(s,n.mapping,n.wrapS,n.wrapT,n.magFilter,n.minFilter,n.format,n.type,n.anisotropy,n.colorSpace);r.flipY=!1,r.generateMipmaps=n.generateMipmaps,r.internalFormat=n.internalFormat,this.textures=[];const a=n.count;for(let o=0;o<a;o++)this.textures[o]=r.clone(),this.textures[o].isRenderTargetTexture=!0;this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this.depthTexture=n.depthTexture,this.samples=n.samples}get texture(){return this.textures[0]}set texture(t){this.textures[0]=t}setSize(t,e,n=1){if(this.width!==t||this.height!==e||this.depth!==n){this.width=t,this.height=e,this.depth=n;for(let s=0,r=this.textures.length;s<r;s++)this.textures[s].image.width=t,this.textures[s].image.height=e,this.textures[s].image.depth=n;this.dispose()}this.viewport.set(0,0,t,e),this.scissor.set(0,0,t,e)}clone(){return new this.constructor().copy(this)}copy(t){this.width=t.width,this.height=t.height,this.depth=t.depth,this.scissor.copy(t.scissor),this.scissorTest=t.scissorTest,this.viewport.copy(t.viewport),this.textures.length=0;for(let n=0,s=t.textures.length;n<s;n++)this.textures[n]=t.textures[n].clone(),this.textures[n].isRenderTargetTexture=!0;const e=Object.assign({},t.texture.image);return this.texture.source=new hu(e),this.depthBuffer=t.depthBuffer,this.stencilBuffer=t.stencilBuffer,this.resolveDepthBuffer=t.resolveDepthBuffer,this.resolveStencilBuffer=t.resolveStencilBuffer,t.depthTexture!==null&&(this.depthTexture=t.depthTexture.clone()),this.samples=t.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class qi extends Pf{constructor(t=1,e=1,n={}){super(t,e,n),this.isWebGLRenderTarget=!0}}class uu extends Ye{constructor(t=null,e=1,n=1,s=1){super(null),this.isDataArrayTexture=!0,this.image={data:t,width:e,height:n,depth:s},this.magFilter=vn,this.minFilter=vn,this.wrapR=On,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(t){this.layerUpdates.add(t)}clearLayerUpdates(){this.layerUpdates.clear()}}class Lf extends Ye{constructor(t=null,e=1,n=1,s=1){super(null),this.isData3DTexture=!0,this.image={data:t,width:e,height:n,depth:s},this.magFilter=vn,this.minFilter=vn,this.wrapR=On,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class Vn{constructor(t=0,e=0,n=0,s=1){this.isQuaternion=!0,this._x=t,this._y=e,this._z=n,this._w=s}static slerpFlat(t,e,n,s,r,a,o){let c=n[s+0],l=n[s+1],h=n[s+2],u=n[s+3];const f=r[a+0],p=r[a+1],g=r[a+2],_=r[a+3];if(o===0){t[e+0]=c,t[e+1]=l,t[e+2]=h,t[e+3]=u;return}if(o===1){t[e+0]=f,t[e+1]=p,t[e+2]=g,t[e+3]=_;return}if(u!==_||c!==f||l!==p||h!==g){let m=1-o;const d=c*f+l*p+h*g+u*_,w=d>=0?1:-1,T=1-d*d;if(T>Number.EPSILON){const F=Math.sqrt(T),P=Math.atan2(F,d*w);m=Math.sin(m*P)/F,o=Math.sin(o*P)/F}const M=o*w;if(c=c*m+f*M,l=l*m+p*M,h=h*m+g*M,u=u*m+_*M,m===1-o){const F=1/Math.sqrt(c*c+l*l+h*h+u*u);c*=F,l*=F,h*=F,u*=F}}t[e]=c,t[e+1]=l,t[e+2]=h,t[e+3]=u}static multiplyQuaternionsFlat(t,e,n,s,r,a){const o=n[s],c=n[s+1],l=n[s+2],h=n[s+3],u=r[a],f=r[a+1],p=r[a+2],g=r[a+3];return t[e]=o*g+h*u+c*p-l*f,t[e+1]=c*g+h*f+l*u-o*p,t[e+2]=l*g+h*p+o*f-c*u,t[e+3]=h*g-o*u-c*f-l*p,t}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get w(){return this._w}set w(t){this._w=t,this._onChangeCallback()}set(t,e,n,s){return this._x=t,this._y=e,this._z=n,this._w=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(t){return this._x=t.x,this._y=t.y,this._z=t.z,this._w=t.w,this._onChangeCallback(),this}setFromEuler(t,e=!0){const n=t._x,s=t._y,r=t._z,a=t._order,o=Math.cos,c=Math.sin,l=o(n/2),h=o(s/2),u=o(r/2),f=c(n/2),p=c(s/2),g=c(r/2);switch(a){case"XYZ":this._x=f*h*u+l*p*g,this._y=l*p*u-f*h*g,this._z=l*h*g+f*p*u,this._w=l*h*u-f*p*g;break;case"YXZ":this._x=f*h*u+l*p*g,this._y=l*p*u-f*h*g,this._z=l*h*g-f*p*u,this._w=l*h*u+f*p*g;break;case"ZXY":this._x=f*h*u-l*p*g,this._y=l*p*u+f*h*g,this._z=l*h*g+f*p*u,this._w=l*h*u-f*p*g;break;case"ZYX":this._x=f*h*u-l*p*g,this._y=l*p*u+f*h*g,this._z=l*h*g-f*p*u,this._w=l*h*u+f*p*g;break;case"YZX":this._x=f*h*u+l*p*g,this._y=l*p*u+f*h*g,this._z=l*h*g-f*p*u,this._w=l*h*u-f*p*g;break;case"XZY":this._x=f*h*u-l*p*g,this._y=l*p*u-f*h*g,this._z=l*h*g+f*p*u,this._w=l*h*u+f*p*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+a)}return e===!0&&this._onChangeCallback(),this}setFromAxisAngle(t,e){const n=e/2,s=Math.sin(n);return this._x=t.x*s,this._y=t.y*s,this._z=t.z*s,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(t){const e=t.elements,n=e[0],s=e[4],r=e[8],a=e[1],o=e[5],c=e[9],l=e[2],h=e[6],u=e[10],f=n+o+u;if(f>0){const p=.5/Math.sqrt(f+1);this._w=.25/p,this._x=(h-c)*p,this._y=(r-l)*p,this._z=(a-s)*p}else if(n>o&&n>u){const p=2*Math.sqrt(1+n-o-u);this._w=(h-c)/p,this._x=.25*p,this._y=(s+a)/p,this._z=(r+l)/p}else if(o>u){const p=2*Math.sqrt(1+o-n-u);this._w=(r-l)/p,this._x=(s+a)/p,this._y=.25*p,this._z=(c+h)/p}else{const p=2*Math.sqrt(1+u-n-o);this._w=(a-s)/p,this._x=(r+l)/p,this._y=(c+h)/p,this._z=.25*p}return this._onChangeCallback(),this}setFromUnitVectors(t,e){let n=t.dot(e)+1;return n<Number.EPSILON?(n=0,Math.abs(t.x)>Math.abs(t.z)?(this._x=-t.y,this._y=t.x,this._z=0,this._w=n):(this._x=0,this._y=-t.z,this._z=t.y,this._w=n)):(this._x=t.y*e.z-t.z*e.y,this._y=t.z*e.x-t.x*e.z,this._z=t.x*e.y-t.y*e.x,this._w=n),this.normalize()}angleTo(t){return 2*Math.acos(Math.abs(qe(this.dot(t),-1,1)))}rotateTowards(t,e){const n=this.angleTo(t);if(n===0)return this;const s=Math.min(1,e/n);return this.slerp(t,s),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(t){return this._x*t._x+this._y*t._y+this._z*t._z+this._w*t._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let t=this.length();return t===0?(this._x=0,this._y=0,this._z=0,this._w=1):(t=1/t,this._x=this._x*t,this._y=this._y*t,this._z=this._z*t,this._w=this._w*t),this._onChangeCallback(),this}multiply(t){return this.multiplyQuaternions(this,t)}premultiply(t){return this.multiplyQuaternions(t,this)}multiplyQuaternions(t,e){const n=t._x,s=t._y,r=t._z,a=t._w,o=e._x,c=e._y,l=e._z,h=e._w;return this._x=n*h+a*o+s*l-r*c,this._y=s*h+a*c+r*o-n*l,this._z=r*h+a*l+n*c-s*o,this._w=a*h-n*o-s*c-r*l,this._onChangeCallback(),this}slerp(t,e){if(e===0)return this;if(e===1)return this.copy(t);const n=this._x,s=this._y,r=this._z,a=this._w;let o=a*t._w+n*t._x+s*t._y+r*t._z;if(o<0?(this._w=-t._w,this._x=-t._x,this._y=-t._y,this._z=-t._z,o=-o):this.copy(t),o>=1)return this._w=a,this._x=n,this._y=s,this._z=r,this;const c=1-o*o;if(c<=Number.EPSILON){const p=1-e;return this._w=p*a+e*this._w,this._x=p*n+e*this._x,this._y=p*s+e*this._y,this._z=p*r+e*this._z,this.normalize(),this}const l=Math.sqrt(c),h=Math.atan2(l,o),u=Math.sin((1-e)*h)/l,f=Math.sin(e*h)/l;return this._w=a*u+this._w*f,this._x=n*u+this._x*f,this._y=s*u+this._y*f,this._z=r*u+this._z*f,this._onChangeCallback(),this}slerpQuaternions(t,e,n){return this.copy(t).slerp(e,n)}random(){const t=2*Math.PI*Math.random(),e=2*Math.PI*Math.random(),n=Math.random(),s=Math.sqrt(1-n),r=Math.sqrt(n);return this.set(s*Math.sin(t),s*Math.cos(t),r*Math.sin(e),r*Math.cos(e))}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._w===this._w}fromArray(t,e=0){return this._x=t[e],this._y=t[e+1],this._z=t[e+2],this._w=t[e+3],this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._w,t}fromBufferAttribute(t,e){return this._x=t.getX(e),this._y=t.getY(e),this._z=t.getZ(e),this._w=t.getW(e),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class L{constructor(t=0,e=0,n=0){L.prototype.isVector3=!0,this.x=t,this.y=e,this.z=n}set(t,e,n){return n===void 0&&(n=this.z),this.x=t,this.y=e,this.z=n,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this}multiplyVectors(t,e){return this.x=t.x*e.x,this.y=t.y*e.y,this.z=t.z*e.z,this}applyEuler(t){return this.applyQuaternion(wl.setFromEuler(t))}applyAxisAngle(t,e){return this.applyQuaternion(wl.setFromAxisAngle(t,e))}applyMatrix3(t){const e=this.x,n=this.y,s=this.z,r=t.elements;return this.x=r[0]*e+r[3]*n+r[6]*s,this.y=r[1]*e+r[4]*n+r[7]*s,this.z=r[2]*e+r[5]*n+r[8]*s,this}applyNormalMatrix(t){return this.applyMatrix3(t).normalize()}applyMatrix4(t){const e=this.x,n=this.y,s=this.z,r=t.elements,a=1/(r[3]*e+r[7]*n+r[11]*s+r[15]);return this.x=(r[0]*e+r[4]*n+r[8]*s+r[12])*a,this.y=(r[1]*e+r[5]*n+r[9]*s+r[13])*a,this.z=(r[2]*e+r[6]*n+r[10]*s+r[14])*a,this}applyQuaternion(t){const e=this.x,n=this.y,s=this.z,r=t.x,a=t.y,o=t.z,c=t.w,l=2*(a*s-o*n),h=2*(o*e-r*s),u=2*(r*n-a*e);return this.x=e+c*l+a*u-o*h,this.y=n+c*h+o*l-r*u,this.z=s+c*u+r*h-a*l,this}project(t){return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix)}unproject(t){return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld)}transformDirection(t){const e=this.x,n=this.y,s=this.z,r=t.elements;return this.x=r[0]*e+r[4]*n+r[8]*s,this.y=r[1]*e+r[5]*n+r[9]*s,this.z=r[2]*e+r[6]*n+r[10]*s,this.normalize()}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this}divideScalar(t){return this.multiplyScalar(1/t)}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this}cross(t){return this.crossVectors(this,t)}crossVectors(t,e){const n=t.x,s=t.y,r=t.z,a=e.x,o=e.y,c=e.z;return this.x=s*c-r*o,this.y=r*a-n*c,this.z=n*o-s*a,this}projectOnVector(t){const e=t.lengthSq();if(e===0)return this.set(0,0,0);const n=t.dot(this)/e;return this.copy(t).multiplyScalar(n)}projectOnPlane(t){return ea.copy(this).projectOnVector(t),this.sub(ea)}reflect(t){return this.sub(ea.copy(t).multiplyScalar(2*this.dot(t)))}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(qe(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y,s=this.z-t.z;return e*e+n*n+s*s}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)+Math.abs(this.z-t.z)}setFromSpherical(t){return this.setFromSphericalCoords(t.radius,t.phi,t.theta)}setFromSphericalCoords(t,e,n){const s=Math.sin(e)*t;return this.x=s*Math.sin(n),this.y=Math.cos(e)*t,this.z=s*Math.cos(n),this}setFromCylindrical(t){return this.setFromCylindricalCoords(t.radius,t.theta,t.y)}setFromCylindricalCoords(t,e,n){return this.x=t*Math.sin(e),this.y=n,this.z=t*Math.cos(e),this}setFromMatrixPosition(t){const e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this}setFromMatrixScale(t){const e=this.setFromMatrixColumn(t,0).length(),n=this.setFromMatrixColumn(t,1).length(),s=this.setFromMatrixColumn(t,2).length();return this.x=e,this.y=n,this.z=s,this}setFromMatrixColumn(t,e){return this.fromArray(t.elements,e*4)}setFromMatrix3Column(t,e){return this.fromArray(t.elements,e*3)}setFromEuler(t){return this.x=t._x,this.y=t._y,this.z=t._z,this}setFromColor(t){return this.x=t.r,this.y=t.g,this.z=t.b,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const t=Math.random()*Math.PI*2,e=Math.random()*2-1,n=Math.sqrt(1-e*e);return this.x=n*Math.cos(t),this.y=e,this.z=n*Math.sin(t),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const ea=new L,wl=new Vn;class Xn{constructor(t=new L(1/0,1/0,1/0),e=new L(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=t,this.max=e}set(t,e){return this.min.copy(t),this.max.copy(e),this}setFromArray(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e+=3)this.expandByPoint(Dn.fromArray(t,e));return this}setFromBufferAttribute(t){this.makeEmpty();for(let e=0,n=t.count;e<n;e++)this.expandByPoint(Dn.fromBufferAttribute(t,e));return this}setFromPoints(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e++)this.expandByPoint(t[e]);return this}setFromCenterAndSize(t,e){const n=Dn.copy(e).multiplyScalar(.5);return this.min.copy(t).sub(n),this.max.copy(t).add(n),this}setFromObject(t,e=!1){return this.makeEmpty(),this.expandByObject(t,e)}clone(){return new this.constructor().copy(this)}copy(t){return this.min.copy(t.min),this.max.copy(t.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(t){return this.isEmpty()?t.set(0,0,0):t.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(t){return this.isEmpty()?t.set(0,0,0):t.subVectors(this.max,this.min)}expandByPoint(t){return this.min.min(t),this.max.max(t),this}expandByVector(t){return this.min.sub(t),this.max.add(t),this}expandByScalar(t){return this.min.addScalar(-t),this.max.addScalar(t),this}expandByObject(t,e=!1){t.updateWorldMatrix(!1,!1);const n=t.geometry;if(n!==void 0){const r=n.getAttribute("position");if(e===!0&&r!==void 0&&t.isInstancedMesh!==!0)for(let a=0,o=r.count;a<o;a++)t.isMesh===!0?t.getVertexPosition(a,Dn):Dn.fromBufferAttribute(r,a),Dn.applyMatrix4(t.matrixWorld),this.expandByPoint(Dn);else t.boundingBox!==void 0?(t.boundingBox===null&&t.computeBoundingBox(),Pr.copy(t.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Pr.copy(n.boundingBox)),Pr.applyMatrix4(t.matrixWorld),this.union(Pr)}const s=t.children;for(let r=0,a=s.length;r<a;r++)this.expandByObject(s[r],e);return this}containsPoint(t){return t.x>=this.min.x&&t.x<=this.max.x&&t.y>=this.min.y&&t.y<=this.max.y&&t.z>=this.min.z&&t.z<=this.max.z}containsBox(t){return this.min.x<=t.min.x&&t.max.x<=this.max.x&&this.min.y<=t.min.y&&t.max.y<=this.max.y&&this.min.z<=t.min.z&&t.max.z<=this.max.z}getParameter(t,e){return e.set((t.x-this.min.x)/(this.max.x-this.min.x),(t.y-this.min.y)/(this.max.y-this.min.y),(t.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(t){return t.max.x>=this.min.x&&t.min.x<=this.max.x&&t.max.y>=this.min.y&&t.min.y<=this.max.y&&t.max.z>=this.min.z&&t.min.z<=this.max.z}intersectsSphere(t){return this.clampPoint(t.center,Dn),Dn.distanceToSquared(t.center)<=t.radius*t.radius}intersectsPlane(t){let e,n;return t.normal.x>0?(e=t.normal.x*this.min.x,n=t.normal.x*this.max.x):(e=t.normal.x*this.max.x,n=t.normal.x*this.min.x),t.normal.y>0?(e+=t.normal.y*this.min.y,n+=t.normal.y*this.max.y):(e+=t.normal.y*this.max.y,n+=t.normal.y*this.min.y),t.normal.z>0?(e+=t.normal.z*this.min.z,n+=t.normal.z*this.max.z):(e+=t.normal.z*this.max.z,n+=t.normal.z*this.min.z),e<=-t.constant&&n>=-t.constant}intersectsTriangle(t){if(this.isEmpty())return!1;this.getCenter(qs),Lr.subVectors(this.max,qs),es.subVectors(t.a,qs),ns.subVectors(t.b,qs),is.subVectors(t.c,qs),gi.subVectors(ns,es),_i.subVectors(is,ns),Ii.subVectors(es,is);let e=[0,-gi.z,gi.y,0,-_i.z,_i.y,0,-Ii.z,Ii.y,gi.z,0,-gi.x,_i.z,0,-_i.x,Ii.z,0,-Ii.x,-gi.y,gi.x,0,-_i.y,_i.x,0,-Ii.y,Ii.x,0];return!na(e,es,ns,is,Lr)||(e=[1,0,0,0,1,0,0,0,1],!na(e,es,ns,is,Lr))?!1:(Nr.crossVectors(gi,_i),e=[Nr.x,Nr.y,Nr.z],na(e,es,ns,is,Lr))}clampPoint(t,e){return e.copy(t).clamp(this.min,this.max)}distanceToPoint(t){return this.clampPoint(t,Dn).distanceTo(t)}getBoundingSphere(t){return this.isEmpty()?t.makeEmpty():(this.getCenter(t.center),t.radius=this.getSize(Dn).length()*.5),t}intersect(t){return this.min.max(t.min),this.max.min(t.max),this.isEmpty()&&this.makeEmpty(),this}union(t){return this.min.min(t.min),this.max.max(t.max),this}applyMatrix4(t){return this.isEmpty()?this:(Kn[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(t),Kn[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(t),Kn[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(t),Kn[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(t),Kn[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(t),Kn[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(t),Kn[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(t),Kn[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(t),this.setFromPoints(Kn),this)}translate(t){return this.min.add(t),this.max.add(t),this}equals(t){return t.min.equals(this.min)&&t.max.equals(this.max)}}const Kn=[new L,new L,new L,new L,new L,new L,new L,new L],Dn=new L,Pr=new Xn,es=new L,ns=new L,is=new L,gi=new L,_i=new L,Ii=new L,qs=new L,Lr=new L,Nr=new L,Ui=new L;function na(i,t,e,n,s){for(let r=0,a=i.length-3;r<=a;r+=3){Ui.fromArray(i,r);const o=s.x*Math.abs(Ui.x)+s.y*Math.abs(Ui.y)+s.z*Math.abs(Ui.z),c=t.dot(Ui),l=e.dot(Ui),h=n.dot(Ui);if(Math.max(-Math.max(c,l,h),Math.min(c,l,h))>o)return!1}return!0}const Nf=new Xn,js=new L,ia=new L;class di{constructor(t=new L,e=-1){this.isSphere=!0,this.center=t,this.radius=e}set(t,e){return this.center.copy(t),this.radius=e,this}setFromPoints(t,e){const n=this.center;e!==void 0?n.copy(e):Nf.setFromPoints(t).getCenter(n);let s=0;for(let r=0,a=t.length;r<a;r++)s=Math.max(s,n.distanceToSquared(t[r]));return this.radius=Math.sqrt(s),this}copy(t){return this.center.copy(t.center),this.radius=t.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(t){return t.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(t){return t.distanceTo(this.center)-this.radius}intersectsSphere(t){const e=this.radius+t.radius;return t.center.distanceToSquared(this.center)<=e*e}intersectsBox(t){return t.intersectsSphere(this)}intersectsPlane(t){return Math.abs(t.distanceToPoint(this.center))<=this.radius}clampPoint(t,e){const n=this.center.distanceToSquared(t);return e.copy(t),n>this.radius*this.radius&&(e.sub(this.center).normalize(),e.multiplyScalar(this.radius).add(this.center)),e}getBoundingBox(t){return this.isEmpty()?(t.makeEmpty(),t):(t.set(this.center,this.center),t.expandByScalar(this.radius),t)}applyMatrix4(t){return this.center.applyMatrix4(t),this.radius=this.radius*t.getMaxScaleOnAxis(),this}translate(t){return this.center.add(t),this}expandByPoint(t){if(this.isEmpty())return this.center.copy(t),this.radius=0,this;js.subVectors(t,this.center);const e=js.lengthSq();if(e>this.radius*this.radius){const n=Math.sqrt(e),s=(n-this.radius)*.5;this.center.addScaledVector(js,s/n),this.radius+=s}return this}union(t){return t.isEmpty()?this:this.isEmpty()?(this.copy(t),this):(this.center.equals(t.center)===!0?this.radius=Math.max(this.radius,t.radius):(ia.subVectors(t.center,this.center).setLength(t.radius),this.expandByPoint(js.copy(t.center).add(ia)),this.expandByPoint(js.copy(t.center).sub(ia))),this)}equals(t){return t.center.equals(this.center)&&t.radius===this.radius}clone(){return new this.constructor().copy(this)}}const Jn=new L,sa=new L,Dr=new L,vi=new L,ra=new L,Ir=new L,oa=new L;class Fs{constructor(t=new L,e=new L(0,0,-1)){this.origin=t,this.direction=e}set(t,e){return this.origin.copy(t),this.direction.copy(e),this}copy(t){return this.origin.copy(t.origin),this.direction.copy(t.direction),this}at(t,e){return e.copy(this.origin).addScaledVector(this.direction,t)}lookAt(t){return this.direction.copy(t).sub(this.origin).normalize(),this}recast(t){return this.origin.copy(this.at(t,Jn)),this}closestPointToPoint(t,e){e.subVectors(t,this.origin);const n=e.dot(this.direction);return n<0?e.copy(this.origin):e.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(t){return Math.sqrt(this.distanceSqToPoint(t))}distanceSqToPoint(t){const e=Jn.subVectors(t,this.origin).dot(this.direction);return e<0?this.origin.distanceToSquared(t):(Jn.copy(this.origin).addScaledVector(this.direction,e),Jn.distanceToSquared(t))}distanceSqToSegment(t,e,n,s){sa.copy(t).add(e).multiplyScalar(.5),Dr.copy(e).sub(t).normalize(),vi.copy(this.origin).sub(sa);const r=t.distanceTo(e)*.5,a=-this.direction.dot(Dr),o=vi.dot(this.direction),c=-vi.dot(Dr),l=vi.lengthSq(),h=Math.abs(1-a*a);let u,f,p,g;if(h>0)if(u=a*c-o,f=a*o-c,g=r*h,u>=0)if(f>=-g)if(f<=g){const _=1/h;u*=_,f*=_,p=u*(u+a*f+2*o)+f*(a*u+f+2*c)+l}else f=r,u=Math.max(0,-(a*f+o)),p=-u*u+f*(f+2*c)+l;else f=-r,u=Math.max(0,-(a*f+o)),p=-u*u+f*(f+2*c)+l;else f<=-g?(u=Math.max(0,-(-a*r+o)),f=u>0?-r:Math.min(Math.max(-r,-c),r),p=-u*u+f*(f+2*c)+l):f<=g?(u=0,f=Math.min(Math.max(-r,-c),r),p=f*(f+2*c)+l):(u=Math.max(0,-(a*r+o)),f=u>0?r:Math.min(Math.max(-r,-c),r),p=-u*u+f*(f+2*c)+l);else f=a>0?-r:r,u=Math.max(0,-(a*f+o)),p=-u*u+f*(f+2*c)+l;return n&&n.copy(this.origin).addScaledVector(this.direction,u),s&&s.copy(sa).addScaledVector(Dr,f),p}intersectSphere(t,e){Jn.subVectors(t.center,this.origin);const n=Jn.dot(this.direction),s=Jn.dot(Jn)-n*n,r=t.radius*t.radius;if(s>r)return null;const a=Math.sqrt(r-s),o=n-a,c=n+a;return c<0?null:o<0?this.at(c,e):this.at(o,e)}intersectsSphere(t){return this.distanceSqToPoint(t.center)<=t.radius*t.radius}distanceToPlane(t){const e=t.normal.dot(this.direction);if(e===0)return t.distanceToPoint(this.origin)===0?0:null;const n=-(this.origin.dot(t.normal)+t.constant)/e;return n>=0?n:null}intersectPlane(t,e){const n=this.distanceToPlane(t);return n===null?null:this.at(n,e)}intersectsPlane(t){const e=t.distanceToPoint(this.origin);return e===0||t.normal.dot(this.direction)*e<0}intersectBox(t,e){let n,s,r,a,o,c;const l=1/this.direction.x,h=1/this.direction.y,u=1/this.direction.z,f=this.origin;return l>=0?(n=(t.min.x-f.x)*l,s=(t.max.x-f.x)*l):(n=(t.max.x-f.x)*l,s=(t.min.x-f.x)*l),h>=0?(r=(t.min.y-f.y)*h,a=(t.max.y-f.y)*h):(r=(t.max.y-f.y)*h,a=(t.min.y-f.y)*h),n>a||r>s||((r>n||isNaN(n))&&(n=r),(a<s||isNaN(s))&&(s=a),u>=0?(o=(t.min.z-f.z)*u,c=(t.max.z-f.z)*u):(o=(t.max.z-f.z)*u,c=(t.min.z-f.z)*u),n>c||o>s)||((o>n||n!==n)&&(n=o),(c<s||s!==s)&&(s=c),s<0)?null:this.at(n>=0?n:s,e)}intersectsBox(t){return this.intersectBox(t,Jn)!==null}intersectTriangle(t,e,n,s,r){ra.subVectors(e,t),Ir.subVectors(n,t),oa.crossVectors(ra,Ir);let a=this.direction.dot(oa),o;if(a>0){if(s)return null;o=1}else if(a<0)o=-1,a=-a;else return null;vi.subVectors(this.origin,t);const c=o*this.direction.dot(Ir.crossVectors(vi,Ir));if(c<0)return null;const l=o*this.direction.dot(ra.cross(vi));if(l<0||c+l>a)return null;const h=-o*vi.dot(oa);return h<0?null:this.at(h/a,r)}applyMatrix4(t){return this.origin.applyMatrix4(t),this.direction.transformDirection(t),this}equals(t){return t.origin.equals(this.origin)&&t.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class jt{constructor(t,e,n,s,r,a,o,c,l,h,u,f,p,g,_,m){jt.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],t!==void 0&&this.set(t,e,n,s,r,a,o,c,l,h,u,f,p,g,_,m)}set(t,e,n,s,r,a,o,c,l,h,u,f,p,g,_,m){const d=this.elements;return d[0]=t,d[4]=e,d[8]=n,d[12]=s,d[1]=r,d[5]=a,d[9]=o,d[13]=c,d[2]=l,d[6]=h,d[10]=u,d[14]=f,d[3]=p,d[7]=g,d[11]=_,d[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new jt().fromArray(this.elements)}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],e[9]=n[9],e[10]=n[10],e[11]=n[11],e[12]=n[12],e[13]=n[13],e[14]=n[14],e[15]=n[15],this}copyPosition(t){const e=this.elements,n=t.elements;return e[12]=n[12],e[13]=n[13],e[14]=n[14],this}setFromMatrix3(t){const e=t.elements;return this.set(e[0],e[3],e[6],0,e[1],e[4],e[7],0,e[2],e[5],e[8],0,0,0,0,1),this}extractBasis(t,e,n){return t.setFromMatrixColumn(this,0),e.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(t,e,n){return this.set(t.x,e.x,n.x,0,t.y,e.y,n.y,0,t.z,e.z,n.z,0,0,0,0,1),this}extractRotation(t){const e=this.elements,n=t.elements,s=1/ss.setFromMatrixColumn(t,0).length(),r=1/ss.setFromMatrixColumn(t,1).length(),a=1/ss.setFromMatrixColumn(t,2).length();return e[0]=n[0]*s,e[1]=n[1]*s,e[2]=n[2]*s,e[3]=0,e[4]=n[4]*r,e[5]=n[5]*r,e[6]=n[6]*r,e[7]=0,e[8]=n[8]*a,e[9]=n[9]*a,e[10]=n[10]*a,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromEuler(t){const e=this.elements,n=t.x,s=t.y,r=t.z,a=Math.cos(n),o=Math.sin(n),c=Math.cos(s),l=Math.sin(s),h=Math.cos(r),u=Math.sin(r);if(t.order==="XYZ"){const f=a*h,p=a*u,g=o*h,_=o*u;e[0]=c*h,e[4]=-c*u,e[8]=l,e[1]=p+g*l,e[5]=f-_*l,e[9]=-o*c,e[2]=_-f*l,e[6]=g+p*l,e[10]=a*c}else if(t.order==="YXZ"){const f=c*h,p=c*u,g=l*h,_=l*u;e[0]=f+_*o,e[4]=g*o-p,e[8]=a*l,e[1]=a*u,e[5]=a*h,e[9]=-o,e[2]=p*o-g,e[6]=_+f*o,e[10]=a*c}else if(t.order==="ZXY"){const f=c*h,p=c*u,g=l*h,_=l*u;e[0]=f-_*o,e[4]=-a*u,e[8]=g+p*o,e[1]=p+g*o,e[5]=a*h,e[9]=_-f*o,e[2]=-a*l,e[6]=o,e[10]=a*c}else if(t.order==="ZYX"){const f=a*h,p=a*u,g=o*h,_=o*u;e[0]=c*h,e[4]=g*l-p,e[8]=f*l+_,e[1]=c*u,e[5]=_*l+f,e[9]=p*l-g,e[2]=-l,e[6]=o*c,e[10]=a*c}else if(t.order==="YZX"){const f=a*c,p=a*l,g=o*c,_=o*l;e[0]=c*h,e[4]=_-f*u,e[8]=g*u+p,e[1]=u,e[5]=a*h,e[9]=-o*h,e[2]=-l*h,e[6]=p*u+g,e[10]=f-_*u}else if(t.order==="XZY"){const f=a*c,p=a*l,g=o*c,_=o*l;e[0]=c*h,e[4]=-u,e[8]=l*h,e[1]=f*u+_,e[5]=a*h,e[9]=p*u-g,e[2]=g*u-p,e[6]=o*h,e[10]=_*u+f}return e[3]=0,e[7]=0,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromQuaternion(t){return this.compose(Df,t,If)}lookAt(t,e,n){const s=this.elements;return mn.subVectors(t,e),mn.lengthSq()===0&&(mn.z=1),mn.normalize(),xi.crossVectors(n,mn),xi.lengthSq()===0&&(Math.abs(n.z)===1?mn.x+=1e-4:mn.z+=1e-4,mn.normalize(),xi.crossVectors(n,mn)),xi.normalize(),Ur.crossVectors(mn,xi),s[0]=xi.x,s[4]=Ur.x,s[8]=mn.x,s[1]=xi.y,s[5]=Ur.y,s[9]=mn.y,s[2]=xi.z,s[6]=Ur.z,s[10]=mn.z,this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,s=e.elements,r=this.elements,a=n[0],o=n[4],c=n[8],l=n[12],h=n[1],u=n[5],f=n[9],p=n[13],g=n[2],_=n[6],m=n[10],d=n[14],w=n[3],T=n[7],M=n[11],F=n[15],P=s[0],N=s[4],D=s[8],y=s[12],S=s[1],U=s[5],k=s[9],H=s[13],J=s[2],Q=s[6],O=s[10],tt=s[14],W=s[3],ct=s[7],ft=s[11],pt=s[15];return r[0]=a*P+o*S+c*J+l*W,r[4]=a*N+o*U+c*Q+l*ct,r[8]=a*D+o*k+c*O+l*ft,r[12]=a*y+o*H+c*tt+l*pt,r[1]=h*P+u*S+f*J+p*W,r[5]=h*N+u*U+f*Q+p*ct,r[9]=h*D+u*k+f*O+p*ft,r[13]=h*y+u*H+f*tt+p*pt,r[2]=g*P+_*S+m*J+d*W,r[6]=g*N+_*U+m*Q+d*ct,r[10]=g*D+_*k+m*O+d*ft,r[14]=g*y+_*H+m*tt+d*pt,r[3]=w*P+T*S+M*J+F*W,r[7]=w*N+T*U+M*Q+F*ct,r[11]=w*D+T*k+M*O+F*ft,r[15]=w*y+T*H+M*tt+F*pt,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[4]*=t,e[8]*=t,e[12]*=t,e[1]*=t,e[5]*=t,e[9]*=t,e[13]*=t,e[2]*=t,e[6]*=t,e[10]*=t,e[14]*=t,e[3]*=t,e[7]*=t,e[11]*=t,e[15]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[4],s=t[8],r=t[12],a=t[1],o=t[5],c=t[9],l=t[13],h=t[2],u=t[6],f=t[10],p=t[14],g=t[3],_=t[7],m=t[11],d=t[15];return g*(+r*c*u-s*l*u-r*o*f+n*l*f+s*o*p-n*c*p)+_*(+e*c*p-e*l*f+r*a*f-s*a*p+s*l*h-r*c*h)+m*(+e*l*u-e*o*p-r*a*u+n*a*p+r*o*h-n*l*h)+d*(-s*o*h-e*c*u+e*o*f+s*a*u-n*a*f+n*c*h)}transpose(){const t=this.elements;let e;return e=t[1],t[1]=t[4],t[4]=e,e=t[2],t[2]=t[8],t[8]=e,e=t[6],t[6]=t[9],t[9]=e,e=t[3],t[3]=t[12],t[12]=e,e=t[7],t[7]=t[13],t[13]=e,e=t[11],t[11]=t[14],t[14]=e,this}setPosition(t,e,n){const s=this.elements;return t.isVector3?(s[12]=t.x,s[13]=t.y,s[14]=t.z):(s[12]=t,s[13]=e,s[14]=n),this}invert(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8],u=t[9],f=t[10],p=t[11],g=t[12],_=t[13],m=t[14],d=t[15],w=u*m*l-_*f*l+_*c*p-o*m*p-u*c*d+o*f*d,T=g*f*l-h*m*l-g*c*p+a*m*p+h*c*d-a*f*d,M=h*_*l-g*u*l+g*o*p-a*_*p-h*o*d+a*u*d,F=g*u*c-h*_*c-g*o*f+a*_*f+h*o*m-a*u*m,P=e*w+n*T+s*M+r*F;if(P===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const N=1/P;return t[0]=w*N,t[1]=(_*f*r-u*m*r-_*s*p+n*m*p+u*s*d-n*f*d)*N,t[2]=(o*m*r-_*c*r+_*s*l-n*m*l-o*s*d+n*c*d)*N,t[3]=(u*c*r-o*f*r-u*s*l+n*f*l+o*s*p-n*c*p)*N,t[4]=T*N,t[5]=(h*m*r-g*f*r+g*s*p-e*m*p-h*s*d+e*f*d)*N,t[6]=(g*c*r-a*m*r-g*s*l+e*m*l+a*s*d-e*c*d)*N,t[7]=(a*f*r-h*c*r+h*s*l-e*f*l-a*s*p+e*c*p)*N,t[8]=M*N,t[9]=(g*u*r-h*_*r-g*n*p+e*_*p+h*n*d-e*u*d)*N,t[10]=(a*_*r-g*o*r+g*n*l-e*_*l-a*n*d+e*o*d)*N,t[11]=(h*o*r-a*u*r-h*n*l+e*u*l+a*n*p-e*o*p)*N,t[12]=F*N,t[13]=(h*_*s-g*u*s+g*n*f-e*_*f-h*n*m+e*u*m)*N,t[14]=(g*o*s-a*_*s-g*n*c+e*_*c+a*n*m-e*o*m)*N,t[15]=(a*u*s-h*o*s+h*n*c-e*u*c-a*n*f+e*o*f)*N,this}scale(t){const e=this.elements,n=t.x,s=t.y,r=t.z;return e[0]*=n,e[4]*=s,e[8]*=r,e[1]*=n,e[5]*=s,e[9]*=r,e[2]*=n,e[6]*=s,e[10]*=r,e[3]*=n,e[7]*=s,e[11]*=r,this}getMaxScaleOnAxis(){const t=this.elements,e=t[0]*t[0]+t[1]*t[1]+t[2]*t[2],n=t[4]*t[4]+t[5]*t[5]+t[6]*t[6],s=t[8]*t[8]+t[9]*t[9]+t[10]*t[10];return Math.sqrt(Math.max(e,n,s))}makeTranslation(t,e,n){return t.isVector3?this.set(1,0,0,t.x,0,1,0,t.y,0,0,1,t.z,0,0,0,1):this.set(1,0,0,t,0,1,0,e,0,0,1,n,0,0,0,1),this}makeRotationX(t){const e=Math.cos(t),n=Math.sin(t);return this.set(1,0,0,0,0,e,-n,0,0,n,e,0,0,0,0,1),this}makeRotationY(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,0,n,0,0,1,0,0,-n,0,e,0,0,0,0,1),this}makeRotationZ(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,0,n,e,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(t,e){const n=Math.cos(e),s=Math.sin(e),r=1-n,a=t.x,o=t.y,c=t.z,l=r*a,h=r*o;return this.set(l*a+n,l*o-s*c,l*c+s*o,0,l*o+s*c,h*o+n,h*c-s*a,0,l*c-s*o,h*c+s*a,r*c*c+n,0,0,0,0,1),this}makeScale(t,e,n){return this.set(t,0,0,0,0,e,0,0,0,0,n,0,0,0,0,1),this}makeShear(t,e,n,s,r,a){return this.set(1,n,r,0,t,1,a,0,e,s,1,0,0,0,0,1),this}compose(t,e,n){const s=this.elements,r=e._x,a=e._y,o=e._z,c=e._w,l=r+r,h=a+a,u=o+o,f=r*l,p=r*h,g=r*u,_=a*h,m=a*u,d=o*u,w=c*l,T=c*h,M=c*u,F=n.x,P=n.y,N=n.z;return s[0]=(1-(_+d))*F,s[1]=(p+M)*F,s[2]=(g-T)*F,s[3]=0,s[4]=(p-M)*P,s[5]=(1-(f+d))*P,s[6]=(m+w)*P,s[7]=0,s[8]=(g+T)*N,s[9]=(m-w)*N,s[10]=(1-(f+_))*N,s[11]=0,s[12]=t.x,s[13]=t.y,s[14]=t.z,s[15]=1,this}decompose(t,e,n){const s=this.elements;let r=ss.set(s[0],s[1],s[2]).length();const a=ss.set(s[4],s[5],s[6]).length(),o=ss.set(s[8],s[9],s[10]).length();this.determinant()<0&&(r=-r),t.x=s[12],t.y=s[13],t.z=s[14],In.copy(this);const l=1/r,h=1/a,u=1/o;return In.elements[0]*=l,In.elements[1]*=l,In.elements[2]*=l,In.elements[4]*=h,In.elements[5]*=h,In.elements[6]*=h,In.elements[8]*=u,In.elements[9]*=u,In.elements[10]*=u,e.setFromRotationMatrix(In),n.x=r,n.y=a,n.z=o,this}makePerspective(t,e,n,s,r,a,o=ri){const c=this.elements,l=2*r/(e-t),h=2*r/(n-s),u=(e+t)/(e-t),f=(n+s)/(n-s);let p,g;if(o===ri)p=-(a+r)/(a-r),g=-2*a*r/(a-r);else if(o===yo)p=-a/(a-r),g=-a*r/(a-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+o);return c[0]=l,c[4]=0,c[8]=u,c[12]=0,c[1]=0,c[5]=h,c[9]=f,c[13]=0,c[2]=0,c[6]=0,c[10]=p,c[14]=g,c[3]=0,c[7]=0,c[11]=-1,c[15]=0,this}makeOrthographic(t,e,n,s,r,a,o=ri){const c=this.elements,l=1/(e-t),h=1/(n-s),u=1/(a-r),f=(e+t)*l,p=(n+s)*h;let g,_;if(o===ri)g=(a+r)*u,_=-2*u;else if(o===yo)g=r*u,_=-1*u;else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+o);return c[0]=2*l,c[4]=0,c[8]=0,c[12]=-f,c[1]=0,c[5]=2*h,c[9]=0,c[13]=-p,c[2]=0,c[6]=0,c[10]=_,c[14]=-g,c[3]=0,c[7]=0,c[11]=0,c[15]=1,this}equals(t){const e=this.elements,n=t.elements;for(let s=0;s<16;s++)if(e[s]!==n[s])return!1;return!0}fromArray(t,e=0){for(let n=0;n<16;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t[e+9]=n[9],t[e+10]=n[10],t[e+11]=n[11],t[e+12]=n[12],t[e+13]=n[13],t[e+14]=n[14],t[e+15]=n[15],t}}const ss=new L,In=new jt,Df=new L(0,0,0),If=new L(1,1,1),xi=new L,Ur=new L,mn=new L,Tl=new jt,Al=new Vn;class fn{constructor(t=0,e=0,n=0,s=fn.DEFAULT_ORDER){this.isEuler=!0,this._x=t,this._y=e,this._z=n,this._order=s}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get order(){return this._order}set order(t){this._order=t,this._onChangeCallback()}set(t,e,n,s=this._order){return this._x=t,this._y=e,this._z=n,this._order=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(t){return this._x=t._x,this._y=t._y,this._z=t._z,this._order=t._order,this._onChangeCallback(),this}setFromRotationMatrix(t,e=this._order,n=!0){const s=t.elements,r=s[0],a=s[4],o=s[8],c=s[1],l=s[5],h=s[9],u=s[2],f=s[6],p=s[10];switch(e){case"XYZ":this._y=Math.asin(qe(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(-h,p),this._z=Math.atan2(-a,r)):(this._x=Math.atan2(f,l),this._z=0);break;case"YXZ":this._x=Math.asin(-qe(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(o,p),this._z=Math.atan2(c,l)):(this._y=Math.atan2(-u,r),this._z=0);break;case"ZXY":this._x=Math.asin(qe(f,-1,1)),Math.abs(f)<.9999999?(this._y=Math.atan2(-u,p),this._z=Math.atan2(-a,l)):(this._y=0,this._z=Math.atan2(c,r));break;case"ZYX":this._y=Math.asin(-qe(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(f,p),this._z=Math.atan2(c,r)):(this._x=0,this._z=Math.atan2(-a,l));break;case"YZX":this._z=Math.asin(qe(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-h,l),this._y=Math.atan2(-u,r)):(this._x=0,this._y=Math.atan2(o,p));break;case"XZY":this._z=Math.asin(-qe(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(f,l),this._y=Math.atan2(o,r)):(this._x=Math.atan2(-h,p),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+e)}return this._order=e,n===!0&&this._onChangeCallback(),this}setFromQuaternion(t,e,n){return Tl.makeRotationFromQuaternion(t),this.setFromRotationMatrix(Tl,e,n)}setFromVector3(t,e=this._order){return this.set(t.x,t.y,t.z,e)}reorder(t){return Al.setFromEuler(this),this.setFromQuaternion(Al,t)}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._order===this._order}fromArray(t){return this._x=t[0],this._y=t[1],this._z=t[2],t[3]!==void 0&&(this._order=t[3]),this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._order,t}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}fn.DEFAULT_ORDER="XYZ";class Gc{constructor(){this.mask=1}set(t){this.mask=(1<<t|0)>>>0}enable(t){this.mask|=1<<t|0}enableAll(){this.mask=-1}toggle(t){this.mask^=1<<t|0}disable(t){this.mask&=~(1<<t|0)}disableAll(){this.mask=0}test(t){return(this.mask&t.mask)!==0}isEnabled(t){return(this.mask&(1<<t|0))!==0}}let Uf=0;const Cl=new L,rs=new Vn,Zn=new jt,Fr=new L,Ys=new L,Ff=new L,Of=new Vn,Rl=new L(1,0,0),Pl=new L(0,1,0),Ll=new L(0,0,1),Nl={type:"added"},kf={type:"removed"},os={type:"childadded",child:null},aa={type:"childremoved",child:null};class Ne extends $i{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:Uf++}),this.uuid=Li(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=Ne.DEFAULT_UP.clone();const t=new L,e=new fn,n=new Vn,s=new L(1,1,1);function r(){n.setFromEuler(e,!1)}function a(){e.setFromQuaternion(n,void 0,!1)}e._onChange(r),n._onChange(a),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:t},rotation:{configurable:!0,enumerable:!0,value:e},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:s},modelViewMatrix:{value:new jt},normalMatrix:{value:new re}}),this.matrix=new jt,this.matrixWorld=new jt,this.matrixAutoUpdate=Ne.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=Ne.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Gc,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(t){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(t),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(t){return this.quaternion.premultiply(t),this}setRotationFromAxisAngle(t,e){this.quaternion.setFromAxisAngle(t,e)}setRotationFromEuler(t){this.quaternion.setFromEuler(t,!0)}setRotationFromMatrix(t){this.quaternion.setFromRotationMatrix(t)}setRotationFromQuaternion(t){this.quaternion.copy(t)}rotateOnAxis(t,e){return rs.setFromAxisAngle(t,e),this.quaternion.multiply(rs),this}rotateOnWorldAxis(t,e){return rs.setFromAxisAngle(t,e),this.quaternion.premultiply(rs),this}rotateX(t){return this.rotateOnAxis(Rl,t)}rotateY(t){return this.rotateOnAxis(Pl,t)}rotateZ(t){return this.rotateOnAxis(Ll,t)}translateOnAxis(t,e){return Cl.copy(t).applyQuaternion(this.quaternion),this.position.add(Cl.multiplyScalar(e)),this}translateX(t){return this.translateOnAxis(Rl,t)}translateY(t){return this.translateOnAxis(Pl,t)}translateZ(t){return this.translateOnAxis(Ll,t)}localToWorld(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(this.matrixWorld)}worldToLocal(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(Zn.copy(this.matrixWorld).invert())}lookAt(t,e,n){t.isVector3?Fr.copy(t):Fr.set(t,e,n);const s=this.parent;this.updateWorldMatrix(!0,!1),Ys.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Zn.lookAt(Ys,Fr,this.up):Zn.lookAt(Fr,Ys,this.up),this.quaternion.setFromRotationMatrix(Zn),s&&(Zn.extractRotation(s.matrixWorld),rs.setFromRotationMatrix(Zn),this.quaternion.premultiply(rs.invert()))}add(t){if(arguments.length>1){for(let e=0;e<arguments.length;e++)this.add(arguments[e]);return this}return t===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",t),this):(t&&t.isObject3D?(t.removeFromParent(),t.parent=this,this.children.push(t),t.dispatchEvent(Nl),os.child=t,this.dispatchEvent(os),os.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",t),this)}remove(t){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}const e=this.children.indexOf(t);return e!==-1&&(t.parent=null,this.children.splice(e,1),t.dispatchEvent(kf),aa.child=t,this.dispatchEvent(aa),aa.child=null),this}removeFromParent(){const t=this.parent;return t!==null&&t.remove(this),this}clear(){return this.remove(...this.children)}attach(t){return this.updateWorldMatrix(!0,!1),Zn.copy(this.matrixWorld).invert(),t.parent!==null&&(t.parent.updateWorldMatrix(!0,!1),Zn.multiply(t.parent.matrixWorld)),t.applyMatrix4(Zn),t.removeFromParent(),t.parent=this,this.children.push(t),t.updateWorldMatrix(!1,!0),t.dispatchEvent(Nl),os.child=t,this.dispatchEvent(os),os.child=null,this}getObjectById(t){return this.getObjectByProperty("id",t)}getObjectByName(t){return this.getObjectByProperty("name",t)}getObjectByProperty(t,e){if(this[t]===e)return this;for(let n=0,s=this.children.length;n<s;n++){const a=this.children[n].getObjectByProperty(t,e);if(a!==void 0)return a}}getObjectsByProperty(t,e,n=[]){this[t]===e&&n.push(this);const s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].getObjectsByProperty(t,e,n);return n}getWorldPosition(t){return this.updateWorldMatrix(!0,!1),t.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Ys,t,Ff),t}getWorldScale(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Ys,Of,t),t}getWorldDirection(t){this.updateWorldMatrix(!0,!1);const e=this.matrixWorld.elements;return t.set(e[8],e[9],e[10]).normalize()}raycast(){}traverse(t){t(this);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].traverse(t)}traverseVisible(t){if(this.visible===!1)return;t(this);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].traverseVisible(t)}traverseAncestors(t){const e=this.parent;e!==null&&(t(e),e.traverseAncestors(t))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(t){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||t)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,t=!0);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].updateMatrixWorld(t)}updateWorldMatrix(t,e){const n=this.parent;if(t===!0&&n!==null&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),e===!0){const s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].updateWorldMatrix(!1,!0)}}toJSON(t){const e=t===void 0||typeof t=="string",n={};e&&(t={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.6,type:"Object",generator:"Object3D.toJSON"});const s={};s.uuid=this.uuid,s.type=this.type,this.name!==""&&(s.name=this.name),this.castShadow===!0&&(s.castShadow=!0),this.receiveShadow===!0&&(s.receiveShadow=!0),this.visible===!1&&(s.visible=!1),this.frustumCulled===!1&&(s.frustumCulled=!1),this.renderOrder!==0&&(s.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(s.userData=this.userData),s.layers=this.layers.mask,s.matrix=this.matrix.toArray(),s.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(s.matrixAutoUpdate=!1),this.isInstancedMesh&&(s.type="InstancedMesh",s.count=this.count,s.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(s.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(s.type="BatchedMesh",s.perObjectFrustumCulled=this.perObjectFrustumCulled,s.sortObjects=this.sortObjects,s.drawRanges=this._drawRanges,s.reservedRanges=this._reservedRanges,s.visibility=this._visibility,s.active=this._active,s.bounds=this._bounds.map(o=>({boxInitialized:o.boxInitialized,boxMin:o.box.min.toArray(),boxMax:o.box.max.toArray(),sphereInitialized:o.sphereInitialized,sphereRadius:o.sphere.radius,sphereCenter:o.sphere.center.toArray()})),s.maxInstanceCount=this._maxInstanceCount,s.maxVertexCount=this._maxVertexCount,s.maxIndexCount=this._maxIndexCount,s.geometryInitialized=this._geometryInitialized,s.geometryCount=this._geometryCount,s.matricesTexture=this._matricesTexture.toJSON(t),this._colorsTexture!==null&&(s.colorsTexture=this._colorsTexture.toJSON(t)),this.boundingSphere!==null&&(s.boundingSphere={center:s.boundingSphere.center.toArray(),radius:s.boundingSphere.radius}),this.boundingBox!==null&&(s.boundingBox={min:s.boundingBox.min.toArray(),max:s.boundingBox.max.toArray()}));function r(o,c){return o[c.uuid]===void 0&&(o[c.uuid]=c.toJSON(t)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?s.background=this.background.toJSON():this.background.isTexture&&(s.background=this.background.toJSON(t).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(s.environment=this.environment.toJSON(t).uuid);else if(this.isMesh||this.isLine||this.isPoints){s.geometry=r(t.geometries,this.geometry);const o=this.geometry.parameters;if(o!==void 0&&o.shapes!==void 0){const c=o.shapes;if(Array.isArray(c))for(let l=0,h=c.length;l<h;l++){const u=c[l];r(t.shapes,u)}else r(t.shapes,c)}}if(this.isSkinnedMesh&&(s.bindMode=this.bindMode,s.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(t.skeletons,this.skeleton),s.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const o=[];for(let c=0,l=this.material.length;c<l;c++)o.push(r(t.materials,this.material[c]));s.material=o}else s.material=r(t.materials,this.material);if(this.children.length>0){s.children=[];for(let o=0;o<this.children.length;o++)s.children.push(this.children[o].toJSON(t).object)}if(this.animations.length>0){s.animations=[];for(let o=0;o<this.animations.length;o++){const c=this.animations[o];s.animations.push(r(t.animations,c))}}if(e){const o=a(t.geometries),c=a(t.materials),l=a(t.textures),h=a(t.images),u=a(t.shapes),f=a(t.skeletons),p=a(t.animations),g=a(t.nodes);o.length>0&&(n.geometries=o),c.length>0&&(n.materials=c),l.length>0&&(n.textures=l),h.length>0&&(n.images=h),u.length>0&&(n.shapes=u),f.length>0&&(n.skeletons=f),p.length>0&&(n.animations=p),g.length>0&&(n.nodes=g)}return n.object=s,n;function a(o){const c=[];for(const l in o){const h=o[l];delete h.metadata,c.push(h)}return c}}clone(t){return new this.constructor().copy(this,t)}copy(t,e=!0){if(this.name=t.name,this.up.copy(t.up),this.position.copy(t.position),this.rotation.order=t.rotation.order,this.quaternion.copy(t.quaternion),this.scale.copy(t.scale),this.matrix.copy(t.matrix),this.matrixWorld.copy(t.matrixWorld),this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrixWorldAutoUpdate=t.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=t.matrixWorldNeedsUpdate,this.layers.mask=t.layers.mask,this.visible=t.visible,this.castShadow=t.castShadow,this.receiveShadow=t.receiveShadow,this.frustumCulled=t.frustumCulled,this.renderOrder=t.renderOrder,this.animations=t.animations.slice(),this.userData=JSON.parse(JSON.stringify(t.userData)),e===!0)for(let n=0;n<t.children.length;n++){const s=t.children[n];this.add(s.clone())}return this}}Ne.DEFAULT_UP=new L(0,1,0);Ne.DEFAULT_MATRIX_AUTO_UPDATE=!0;Ne.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;const Un=new L,Qn=new L,ca=new L,ti=new L,as=new L,cs=new L,Dl=new L,la=new L,ha=new L,ua=new L,da=new xe,fa=new xe,pa=new xe;class Fn{constructor(t=new L,e=new L,n=new L){this.a=t,this.b=e,this.c=n}static getNormal(t,e,n,s){s.subVectors(n,e),Un.subVectors(t,e),s.cross(Un);const r=s.lengthSq();return r>0?s.multiplyScalar(1/Math.sqrt(r)):s.set(0,0,0)}static getBarycoord(t,e,n,s,r){Un.subVectors(s,e),Qn.subVectors(n,e),ca.subVectors(t,e);const a=Un.dot(Un),o=Un.dot(Qn),c=Un.dot(ca),l=Qn.dot(Qn),h=Qn.dot(ca),u=a*l-o*o;if(u===0)return r.set(0,0,0),null;const f=1/u,p=(l*c-o*h)*f,g=(a*h-o*c)*f;return r.set(1-p-g,g,p)}static containsPoint(t,e,n,s){return this.getBarycoord(t,e,n,s,ti)===null?!1:ti.x>=0&&ti.y>=0&&ti.x+ti.y<=1}static getInterpolation(t,e,n,s,r,a,o,c){return this.getBarycoord(t,e,n,s,ti)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(r,ti.x),c.addScaledVector(a,ti.y),c.addScaledVector(o,ti.z),c)}static getInterpolatedAttribute(t,e,n,s,r,a){return da.setScalar(0),fa.setScalar(0),pa.setScalar(0),da.fromBufferAttribute(t,e),fa.fromBufferAttribute(t,n),pa.fromBufferAttribute(t,s),a.setScalar(0),a.addScaledVector(da,r.x),a.addScaledVector(fa,r.y),a.addScaledVector(pa,r.z),a}static isFrontFacing(t,e,n,s){return Un.subVectors(n,e),Qn.subVectors(t,e),Un.cross(Qn).dot(s)<0}set(t,e,n){return this.a.copy(t),this.b.copy(e),this.c.copy(n),this}setFromPointsAndIndices(t,e,n,s){return this.a.copy(t[e]),this.b.copy(t[n]),this.c.copy(t[s]),this}setFromAttributeAndIndices(t,e,n,s){return this.a.fromBufferAttribute(t,e),this.b.fromBufferAttribute(t,n),this.c.fromBufferAttribute(t,s),this}clone(){return new this.constructor().copy(this)}copy(t){return this.a.copy(t.a),this.b.copy(t.b),this.c.copy(t.c),this}getArea(){return Un.subVectors(this.c,this.b),Qn.subVectors(this.a,this.b),Un.cross(Qn).length()*.5}getMidpoint(t){return t.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(t){return Fn.getNormal(this.a,this.b,this.c,t)}getPlane(t){return t.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(t,e){return Fn.getBarycoord(t,this.a,this.b,this.c,e)}getInterpolation(t,e,n,s,r){return Fn.getInterpolation(t,this.a,this.b,this.c,e,n,s,r)}containsPoint(t){return Fn.containsPoint(t,this.a,this.b,this.c)}isFrontFacing(t){return Fn.isFrontFacing(this.a,this.b,this.c,t)}intersectsBox(t){return t.intersectsTriangle(this)}closestPointToPoint(t,e){const n=this.a,s=this.b,r=this.c;let a,o;as.subVectors(s,n),cs.subVectors(r,n),la.subVectors(t,n);const c=as.dot(la),l=cs.dot(la);if(c<=0&&l<=0)return e.copy(n);ha.subVectors(t,s);const h=as.dot(ha),u=cs.dot(ha);if(h>=0&&u<=h)return e.copy(s);const f=c*u-h*l;if(f<=0&&c>=0&&h<=0)return a=c/(c-h),e.copy(n).addScaledVector(as,a);ua.subVectors(t,r);const p=as.dot(ua),g=cs.dot(ua);if(g>=0&&p<=g)return e.copy(r);const _=p*l-c*g;if(_<=0&&l>=0&&g<=0)return o=l/(l-g),e.copy(n).addScaledVector(cs,o);const m=h*g-p*u;if(m<=0&&u-h>=0&&p-g>=0)return Dl.subVectors(r,s),o=(u-h)/(u-h+(p-g)),e.copy(s).addScaledVector(Dl,o);const d=1/(m+_+f);return a=_*d,o=f*d,e.copy(n).addScaledVector(as,a).addScaledVector(cs,o)}equals(t){return t.a.equals(this.a)&&t.b.equals(this.b)&&t.c.equals(this.c)}}const du={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},yi={h:0,s:0,l:0},Or={h:0,s:0,l:0};function ma(i,t,e){return e<0&&(e+=1),e>1&&(e-=1),e<1/6?i+(t-i)*6*e:e<1/2?t:e<2/3?i+(t-i)*6*(2/3-e):i}class Kt{constructor(t,e,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(t,e,n)}set(t,e,n){if(e===void 0&&n===void 0){const s=t;s&&s.isColor?this.copy(s):typeof s=="number"?this.setHex(s):typeof s=="string"&&this.setStyle(s)}else this.setRGB(t,e,n);return this}setScalar(t){return this.r=t,this.g=t,this.b=t,this}setHex(t,e=Le){return t=Math.floor(t),this.r=(t>>16&255)/255,this.g=(t>>8&255)/255,this.b=(t&255)/255,le.toWorkingColorSpace(this,e),this}setRGB(t,e,n,s=le.workingColorSpace){return this.r=t,this.g=e,this.b=n,le.toWorkingColorSpace(this,s),this}setHSL(t,e,n,s=le.workingColorSpace){if(t=Hc(t,1),e=qe(e,0,1),n=qe(n,0,1),e===0)this.r=this.g=this.b=n;else{const r=n<=.5?n*(1+e):n+e-n*e,a=2*n-r;this.r=ma(a,r,t+1/3),this.g=ma(a,r,t),this.b=ma(a,r,t-1/3)}return le.toWorkingColorSpace(this,s),this}setStyle(t,e=Le){function n(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+t+" will be ignored.")}let s;if(s=/^(\w+)\(([^\)]*)\)/.exec(t)){let r;const a=s[1],o=s[2];switch(a){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,e);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,e);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,e);break;default:console.warn("THREE.Color: Unknown color model "+t)}}else if(s=/^\#([A-Fa-f\d]+)$/.exec(t)){const r=s[1],a=r.length;if(a===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,e);if(a===6)return this.setHex(parseInt(r,16),e);console.warn("THREE.Color: Invalid hex color "+t)}else if(t&&t.length>0)return this.setColorName(t,e);return this}setColorName(t,e=Le){const n=du[t.toLowerCase()];return n!==void 0?this.setHex(n,e):console.warn("THREE.Color: Unknown color "+t),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(t){return this.r=t.r,this.g=t.g,this.b=t.b,this}copySRGBToLinear(t){return this.r=oi(t.r),this.g=oi(t.g),this.b=oi(t.b),this}copyLinearToSRGB(t){return this.r=ys(t.r),this.g=ys(t.g),this.b=ys(t.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(t=Le){return le.fromWorkingColorSpace(Ke.copy(this),t),Math.round(qe(Ke.r*255,0,255))*65536+Math.round(qe(Ke.g*255,0,255))*256+Math.round(qe(Ke.b*255,0,255))}getHexString(t=Le){return("000000"+this.getHex(t).toString(16)).slice(-6)}getHSL(t,e=le.workingColorSpace){le.fromWorkingColorSpace(Ke.copy(this),e);const n=Ke.r,s=Ke.g,r=Ke.b,a=Math.max(n,s,r),o=Math.min(n,s,r);let c,l;const h=(o+a)/2;if(o===a)c=0,l=0;else{const u=a-o;switch(l=h<=.5?u/(a+o):u/(2-a-o),a){case n:c=(s-r)/u+(s<r?6:0);break;case s:c=(r-n)/u+2;break;case r:c=(n-s)/u+4;break}c/=6}return t.h=c,t.s=l,t.l=h,t}getRGB(t,e=le.workingColorSpace){return le.fromWorkingColorSpace(Ke.copy(this),e),t.r=Ke.r,t.g=Ke.g,t.b=Ke.b,t}getStyle(t=Le){le.fromWorkingColorSpace(Ke.copy(this),t);const e=Ke.r,n=Ke.g,s=Ke.b;return t!==Le?`color(${t} ${e.toFixed(3)} ${n.toFixed(3)} ${s.toFixed(3)})`:`rgb(${Math.round(e*255)},${Math.round(n*255)},${Math.round(s*255)})`}offsetHSL(t,e,n){return this.getHSL(yi),this.setHSL(yi.h+t,yi.s+e,yi.l+n)}add(t){return this.r+=t.r,this.g+=t.g,this.b+=t.b,this}addColors(t,e){return this.r=t.r+e.r,this.g=t.g+e.g,this.b=t.b+e.b,this}addScalar(t){return this.r+=t,this.g+=t,this.b+=t,this}sub(t){return this.r=Math.max(0,this.r-t.r),this.g=Math.max(0,this.g-t.g),this.b=Math.max(0,this.b-t.b),this}multiply(t){return this.r*=t.r,this.g*=t.g,this.b*=t.b,this}multiplyScalar(t){return this.r*=t,this.g*=t,this.b*=t,this}lerp(t,e){return this.r+=(t.r-this.r)*e,this.g+=(t.g-this.g)*e,this.b+=(t.b-this.b)*e,this}lerpColors(t,e,n){return this.r=t.r+(e.r-t.r)*n,this.g=t.g+(e.g-t.g)*n,this.b=t.b+(e.b-t.b)*n,this}lerpHSL(t,e){this.getHSL(yi),t.getHSL(Or);const n=sr(yi.h,Or.h,e),s=sr(yi.s,Or.s,e),r=sr(yi.l,Or.l,e);return this.setHSL(n,s,r),this}setFromVector3(t){return this.r=t.x,this.g=t.y,this.b=t.z,this}applyMatrix3(t){const e=this.r,n=this.g,s=this.b,r=t.elements;return this.r=r[0]*e+r[3]*n+r[6]*s,this.g=r[1]*e+r[4]*n+r[7]*s,this.b=r[2]*e+r[5]*n+r[8]*s,this}equals(t){return t.r===this.r&&t.g===this.g&&t.b===this.b}fromArray(t,e=0){return this.r=t[e],this.g=t[e+1],this.b=t[e+2],this}toArray(t=[],e=0){return t[e]=this.r,t[e+1]=this.g,t[e+2]=this.b,t}fromBufferAttribute(t,e){return this.r=t.getX(e),this.g=t.getY(e),this.b=t.getZ(e),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const Ke=new Kt;Kt.NAMES=du;let Bf=0;class Hn extends $i{static get type(){return"Material"}get type(){return this.constructor.type}set type(t){}constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:Bf++}),this.uuid=Li(),this.name="",this.blending=vs,this.side=ai,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Va,this.blendDst=Ha,this.blendEquation=Hi,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Kt(0,0,0),this.blendAlpha=0,this.depthFunc=ws,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=ml,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Qi,this.stencilZFail=Qi,this.stencilZPass=Qi,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(t){this._alphaTest>0!=t>0&&this.version++,this._alphaTest=t}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(t){if(t!==void 0)for(const e in t){const n=t[e];if(n===void 0){console.warn(`THREE.Material: parameter '${e}' has value of undefined.`);continue}const s=this[e];if(s===void 0){console.warn(`THREE.Material: '${e}' is not a property of THREE.${this.type}.`);continue}s&&s.isColor?s.set(n):s&&s.isVector3&&n&&n.isVector3?s.copy(n):this[e]=n}}toJSON(t){const e=t===void 0||typeof t=="string";e&&(t={textures:{},images:{}});const n={metadata:{version:4.6,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(t).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(t).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(t).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(t).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(t).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(t).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(t).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(t).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(t).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(t).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(t).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(t).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(t).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(t).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(t).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(t).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(t).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(t).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(t).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(t).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(t).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(t).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(t).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(t).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==vs&&(n.blending=this.blending),this.side!==ai&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==Va&&(n.blendSrc=this.blendSrc),this.blendDst!==Ha&&(n.blendDst=this.blendDst),this.blendEquation!==Hi&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==ws&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==ml&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Qi&&(n.stencilFail=this.stencilFail),this.stencilZFail!==Qi&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==Qi&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function s(r){const a=[];for(const o in r){const c=r[o];delete c.metadata,a.push(c)}return a}if(e){const r=s(t.textures),a=s(t.images);r.length>0&&(n.textures=r),a.length>0&&(n.images=a)}return n}clone(){return new this.constructor().copy(this)}copy(t){this.name=t.name,this.blending=t.blending,this.side=t.side,this.vertexColors=t.vertexColors,this.opacity=t.opacity,this.transparent=t.transparent,this.blendSrc=t.blendSrc,this.blendDst=t.blendDst,this.blendEquation=t.blendEquation,this.blendSrcAlpha=t.blendSrcAlpha,this.blendDstAlpha=t.blendDstAlpha,this.blendEquationAlpha=t.blendEquationAlpha,this.blendColor.copy(t.blendColor),this.blendAlpha=t.blendAlpha,this.depthFunc=t.depthFunc,this.depthTest=t.depthTest,this.depthWrite=t.depthWrite,this.stencilWriteMask=t.stencilWriteMask,this.stencilFunc=t.stencilFunc,this.stencilRef=t.stencilRef,this.stencilFuncMask=t.stencilFuncMask,this.stencilFail=t.stencilFail,this.stencilZFail=t.stencilZFail,this.stencilZPass=t.stencilZPass,this.stencilWrite=t.stencilWrite;const e=t.clippingPlanes;let n=null;if(e!==null){const s=e.length;n=new Array(s);for(let r=0;r!==s;++r)n[r]=e[r].clone()}return this.clippingPlanes=n,this.clipIntersection=t.clipIntersection,this.clipShadows=t.clipShadows,this.shadowSide=t.shadowSide,this.colorWrite=t.colorWrite,this.precision=t.precision,this.polygonOffset=t.polygonOffset,this.polygonOffsetFactor=t.polygonOffsetFactor,this.polygonOffsetUnits=t.polygonOffsetUnits,this.dithering=t.dithering,this.alphaTest=t.alphaTest,this.alphaHash=t.alphaHash,this.alphaToCoverage=t.alphaToCoverage,this.premultipliedAlpha=t.premultipliedAlpha,this.forceSinglePass=t.forceSinglePass,this.visible=t.visible,this.toneMapped=t.toneMapped,this.userData=JSON.parse(JSON.stringify(t.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(t){t===!0&&this.version++}onBuild(){console.warn("Material: onBuild() has been removed.")}}class je extends Hn{static get type(){return"MeshBasicMaterial"}constructor(t){super(),this.isMeshBasicMaterial=!0,this.color=new Kt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new fn,this.combine=Uo,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.fog=t.fog,this}}const Be=new L,kr=new At;class xn{constructor(t,e,n=!1){if(Array.isArray(t))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,this.name="",this.array=t,this.itemSize=e,this.count=t!==void 0?t.length/e:0,this.normalized=n,this.usage=gl,this.updateRanges=[],this.gpuType=Wn,this.version=0}onUploadCallback(){}set needsUpdate(t){t===!0&&this.version++}setUsage(t){return this.usage=t,this}addUpdateRange(t,e){this.updateRanges.push({start:t,count:e})}clearUpdateRanges(){this.updateRanges.length=0}copy(t){return this.name=t.name,this.array=new t.array.constructor(t.array),this.itemSize=t.itemSize,this.count=t.count,this.normalized=t.normalized,this.usage=t.usage,this.gpuType=t.gpuType,this}copyAt(t,e,n){t*=this.itemSize,n*=e.itemSize;for(let s=0,r=this.itemSize;s<r;s++)this.array[t+s]=e.array[n+s];return this}copyArray(t){return this.array.set(t),this}applyMatrix3(t){if(this.itemSize===2)for(let e=0,n=this.count;e<n;e++)kr.fromBufferAttribute(this,e),kr.applyMatrix3(t),this.setXY(e,kr.x,kr.y);else if(this.itemSize===3)for(let e=0,n=this.count;e<n;e++)Be.fromBufferAttribute(this,e),Be.applyMatrix3(t),this.setXYZ(e,Be.x,Be.y,Be.z);return this}applyMatrix4(t){for(let e=0,n=this.count;e<n;e++)Be.fromBufferAttribute(this,e),Be.applyMatrix4(t),this.setXYZ(e,Be.x,Be.y,Be.z);return this}applyNormalMatrix(t){for(let e=0,n=this.count;e<n;e++)Be.fromBufferAttribute(this,e),Be.applyNormalMatrix(t),this.setXYZ(e,Be.x,Be.y,Be.z);return this}transformDirection(t){for(let e=0,n=this.count;e<n;e++)Be.fromBufferAttribute(this,e),Be.transformDirection(t),this.setXYZ(e,Be.x,Be.y,Be.z);return this}set(t,e=0){return this.array.set(t,e),this}getComponent(t,e){let n=this.array[t*this.itemSize+e];return this.normalized&&(n=fs(n,this.array)),n}setComponent(t,e,n){return this.normalized&&(n=tn(n,this.array)),this.array[t*this.itemSize+e]=n,this}getX(t){let e=this.array[t*this.itemSize];return this.normalized&&(e=fs(e,this.array)),e}setX(t,e){return this.normalized&&(e=tn(e,this.array)),this.array[t*this.itemSize]=e,this}getY(t){let e=this.array[t*this.itemSize+1];return this.normalized&&(e=fs(e,this.array)),e}setY(t,e){return this.normalized&&(e=tn(e,this.array)),this.array[t*this.itemSize+1]=e,this}getZ(t){let e=this.array[t*this.itemSize+2];return this.normalized&&(e=fs(e,this.array)),e}setZ(t,e){return this.normalized&&(e=tn(e,this.array)),this.array[t*this.itemSize+2]=e,this}getW(t){let e=this.array[t*this.itemSize+3];return this.normalized&&(e=fs(e,this.array)),e}setW(t,e){return this.normalized&&(e=tn(e,this.array)),this.array[t*this.itemSize+3]=e,this}setXY(t,e,n){return t*=this.itemSize,this.normalized&&(e=tn(e,this.array),n=tn(n,this.array)),this.array[t+0]=e,this.array[t+1]=n,this}setXYZ(t,e,n,s){return t*=this.itemSize,this.normalized&&(e=tn(e,this.array),n=tn(n,this.array),s=tn(s,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=s,this}setXYZW(t,e,n,s,r){return t*=this.itemSize,this.normalized&&(e=tn(e,this.array),n=tn(n,this.array),s=tn(s,this.array),r=tn(r,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=s,this.array[t+3]=r,this}onUpload(t){return this.onUploadCallback=t,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const t={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(t.name=this.name),this.usage!==gl&&(t.usage=this.usage),t}}class fu extends xn{constructor(t,e,n){super(new Uint16Array(t),e,n)}}class pu extends xn{constructor(t,e,n){super(new Uint32Array(t),e,n)}}class ne extends xn{constructor(t,e,n){super(new Float32Array(t),e,n)}}let zf=0;const bn=new jt,ga=new Ne,ls=new L,gn=new Xn,$s=new Xn,Xe=new L;class Pe extends $i{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:zf++}),this.uuid=Li(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(t){return Array.isArray(t)?this.index=new(lu(t)?pu:fu)(t,1):this.index=t,this}setIndirect(t){return this.indirect=t,this}getIndirect(){return this.indirect}getAttribute(t){return this.attributes[t]}setAttribute(t,e){return this.attributes[t]=e,this}deleteAttribute(t){return delete this.attributes[t],this}hasAttribute(t){return this.attributes[t]!==void 0}addGroup(t,e,n=0){this.groups.push({start:t,count:e,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(t,e){this.drawRange.start=t,this.drawRange.count=e}applyMatrix4(t){const e=this.attributes.position;e!==void 0&&(e.applyMatrix4(t),e.needsUpdate=!0);const n=this.attributes.normal;if(n!==void 0){const r=new re().getNormalMatrix(t);n.applyNormalMatrix(r),n.needsUpdate=!0}const s=this.attributes.tangent;return s!==void 0&&(s.transformDirection(t),s.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(t){return bn.makeRotationFromQuaternion(t),this.applyMatrix4(bn),this}rotateX(t){return bn.makeRotationX(t),this.applyMatrix4(bn),this}rotateY(t){return bn.makeRotationY(t),this.applyMatrix4(bn),this}rotateZ(t){return bn.makeRotationZ(t),this.applyMatrix4(bn),this}translate(t,e,n){return bn.makeTranslation(t,e,n),this.applyMatrix4(bn),this}scale(t,e,n){return bn.makeScale(t,e,n),this.applyMatrix4(bn),this}lookAt(t){return ga.lookAt(t),ga.updateMatrix(),this.applyMatrix4(ga.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(ls).negate(),this.translate(ls.x,ls.y,ls.z),this}setFromPoints(t){const e=this.getAttribute("position");if(e===void 0){const n=[];for(let s=0,r=t.length;s<r;s++){const a=t[s];n.push(a.x,a.y,a.z||0)}this.setAttribute("position",new ne(n,3))}else{for(let n=0,s=e.count;n<s;n++){const r=t[n];e.setXYZ(n,r.x,r.y,r.z||0)}t.length>e.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),e.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Xn);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new L(-1/0,-1/0,-1/0),new L(1/0,1/0,1/0));return}if(t!==void 0){if(this.boundingBox.setFromBufferAttribute(t),e)for(let n=0,s=e.length;n<s;n++){const r=e[n];gn.setFromBufferAttribute(r),this.morphTargetsRelative?(Xe.addVectors(this.boundingBox.min,gn.min),this.boundingBox.expandByPoint(Xe),Xe.addVectors(this.boundingBox.max,gn.max),this.boundingBox.expandByPoint(Xe)):(this.boundingBox.expandByPoint(gn.min),this.boundingBox.expandByPoint(gn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new di);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new L,1/0);return}if(t){const n=this.boundingSphere.center;if(gn.setFromBufferAttribute(t),e)for(let r=0,a=e.length;r<a;r++){const o=e[r];$s.setFromBufferAttribute(o),this.morphTargetsRelative?(Xe.addVectors(gn.min,$s.min),gn.expandByPoint(Xe),Xe.addVectors(gn.max,$s.max),gn.expandByPoint(Xe)):(gn.expandByPoint($s.min),gn.expandByPoint($s.max))}gn.getCenter(n);let s=0;for(let r=0,a=t.count;r<a;r++)Xe.fromBufferAttribute(t,r),s=Math.max(s,n.distanceToSquared(Xe));if(e)for(let r=0,a=e.length;r<a;r++){const o=e[r],c=this.morphTargetsRelative;for(let l=0,h=o.count;l<h;l++)Xe.fromBufferAttribute(o,l),c&&(ls.fromBufferAttribute(t,l),Xe.add(ls)),s=Math.max(s,n.distanceToSquared(Xe))}this.boundingSphere.radius=Math.sqrt(s),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const t=this.index,e=this.attributes;if(t===null||e.position===void 0||e.normal===void 0||e.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const n=e.position,s=e.normal,r=e.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new xn(new Float32Array(4*n.count),4));const a=this.getAttribute("tangent"),o=[],c=[];for(let D=0;D<n.count;D++)o[D]=new L,c[D]=new L;const l=new L,h=new L,u=new L,f=new At,p=new At,g=new At,_=new L,m=new L;function d(D,y,S){l.fromBufferAttribute(n,D),h.fromBufferAttribute(n,y),u.fromBufferAttribute(n,S),f.fromBufferAttribute(r,D),p.fromBufferAttribute(r,y),g.fromBufferAttribute(r,S),h.sub(l),u.sub(l),p.sub(f),g.sub(f);const U=1/(p.x*g.y-g.x*p.y);isFinite(U)&&(_.copy(h).multiplyScalar(g.y).addScaledVector(u,-p.y).multiplyScalar(U),m.copy(u).multiplyScalar(p.x).addScaledVector(h,-g.x).multiplyScalar(U),o[D].add(_),o[y].add(_),o[S].add(_),c[D].add(m),c[y].add(m),c[S].add(m))}let w=this.groups;w.length===0&&(w=[{start:0,count:t.count}]);for(let D=0,y=w.length;D<y;++D){const S=w[D],U=S.start,k=S.count;for(let H=U,J=U+k;H<J;H+=3)d(t.getX(H+0),t.getX(H+1),t.getX(H+2))}const T=new L,M=new L,F=new L,P=new L;function N(D){F.fromBufferAttribute(s,D),P.copy(F);const y=o[D];T.copy(y),T.sub(F.multiplyScalar(F.dot(y))).normalize(),M.crossVectors(P,y);const U=M.dot(c[D])<0?-1:1;a.setXYZW(D,T.x,T.y,T.z,U)}for(let D=0,y=w.length;D<y;++D){const S=w[D],U=S.start,k=S.count;for(let H=U,J=U+k;H<J;H+=3)N(t.getX(H+0)),N(t.getX(H+1)),N(t.getX(H+2))}}computeVertexNormals(){const t=this.index,e=this.getAttribute("position");if(e!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new xn(new Float32Array(e.count*3),3),this.setAttribute("normal",n);else for(let f=0,p=n.count;f<p;f++)n.setXYZ(f,0,0,0);const s=new L,r=new L,a=new L,o=new L,c=new L,l=new L,h=new L,u=new L;if(t)for(let f=0,p=t.count;f<p;f+=3){const g=t.getX(f+0),_=t.getX(f+1),m=t.getX(f+2);s.fromBufferAttribute(e,g),r.fromBufferAttribute(e,_),a.fromBufferAttribute(e,m),h.subVectors(a,r),u.subVectors(s,r),h.cross(u),o.fromBufferAttribute(n,g),c.fromBufferAttribute(n,_),l.fromBufferAttribute(n,m),o.add(h),c.add(h),l.add(h),n.setXYZ(g,o.x,o.y,o.z),n.setXYZ(_,c.x,c.y,c.z),n.setXYZ(m,l.x,l.y,l.z)}else for(let f=0,p=e.count;f<p;f+=3)s.fromBufferAttribute(e,f+0),r.fromBufferAttribute(e,f+1),a.fromBufferAttribute(e,f+2),h.subVectors(a,r),u.subVectors(s,r),h.cross(u),n.setXYZ(f+0,h.x,h.y,h.z),n.setXYZ(f+1,h.x,h.y,h.z),n.setXYZ(f+2,h.x,h.y,h.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){const t=this.attributes.normal;for(let e=0,n=t.count;e<n;e++)Xe.fromBufferAttribute(t,e),Xe.normalize(),t.setXYZ(e,Xe.x,Xe.y,Xe.z)}toNonIndexed(){function t(o,c){const l=o.array,h=o.itemSize,u=o.normalized,f=new l.constructor(c.length*h);let p=0,g=0;for(let _=0,m=c.length;_<m;_++){o.isInterleavedBufferAttribute?p=c[_]*o.data.stride+o.offset:p=c[_]*h;for(let d=0;d<h;d++)f[g++]=l[p++]}return new xn(f,h,u)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const e=new Pe,n=this.index.array,s=this.attributes;for(const o in s){const c=s[o],l=t(c,n);e.setAttribute(o,l)}const r=this.morphAttributes;for(const o in r){const c=[],l=r[o];for(let h=0,u=l.length;h<u;h++){const f=l[h],p=t(f,n);c.push(p)}e.morphAttributes[o]=c}e.morphTargetsRelative=this.morphTargetsRelative;const a=this.groups;for(let o=0,c=a.length;o<c;o++){const l=a[o];e.addGroup(l.start,l.count,l.materialIndex)}return e}toJSON(){const t={metadata:{version:4.6,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(t.uuid=this.uuid,t.type=this.type,this.name!==""&&(t.name=this.name),Object.keys(this.userData).length>0&&(t.userData=this.userData),this.parameters!==void 0){const c=this.parameters;for(const l in c)c[l]!==void 0&&(t[l]=c[l]);return t}t.data={attributes:{}};const e=this.index;e!==null&&(t.data.index={type:e.array.constructor.name,array:Array.prototype.slice.call(e.array)});const n=this.attributes;for(const c in n){const l=n[c];t.data.attributes[c]=l.toJSON(t.data)}const s={};let r=!1;for(const c in this.morphAttributes){const l=this.morphAttributes[c],h=[];for(let u=0,f=l.length;u<f;u++){const p=l[u];h.push(p.toJSON(t.data))}h.length>0&&(s[c]=h,r=!0)}r&&(t.data.morphAttributes=s,t.data.morphTargetsRelative=this.morphTargetsRelative);const a=this.groups;a.length>0&&(t.data.groups=JSON.parse(JSON.stringify(a)));const o=this.boundingSphere;return o!==null&&(t.data.boundingSphere={center:o.center.toArray(),radius:o.radius}),t}clone(){return new this.constructor().copy(this)}copy(t){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const e={};this.name=t.name;const n=t.index;n!==null&&this.setIndex(n.clone(e));const s=t.attributes;for(const l in s){const h=s[l];this.setAttribute(l,h.clone(e))}const r=t.morphAttributes;for(const l in r){const h=[],u=r[l];for(let f=0,p=u.length;f<p;f++)h.push(u[f].clone(e));this.morphAttributes[l]=h}this.morphTargetsRelative=t.morphTargetsRelative;const a=t.groups;for(let l=0,h=a.length;l<h;l++){const u=a[l];this.addGroup(u.start,u.count,u.materialIndex)}const o=t.boundingBox;o!==null&&(this.boundingBox=o.clone());const c=t.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=t.drawRange.start,this.drawRange.count=t.drawRange.count,this.userData=t.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}const Il=new jt,Fi=new Fs,Br=new di,Ul=new L,zr=new L,Vr=new L,Hr=new L,_a=new L,Gr=new L,Fl=new L,Wr=new L;class me extends Ne{constructor(t=new Pe,e=new je){super(),this.isMesh=!0,this.type="Mesh",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),t.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=t.morphTargetInfluences.slice()),t.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},t.morphTargetDictionary)),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}getVertexPosition(t,e){const n=this.geometry,s=n.attributes.position,r=n.morphAttributes.position,a=n.morphTargetsRelative;e.fromBufferAttribute(s,t);const o=this.morphTargetInfluences;if(r&&o){Gr.set(0,0,0);for(let c=0,l=r.length;c<l;c++){const h=o[c],u=r[c];h!==0&&(_a.fromBufferAttribute(u,t),a?Gr.addScaledVector(_a,h):Gr.addScaledVector(_a.sub(e),h))}e.add(Gr)}return e}raycast(t,e){const n=this.geometry,s=this.material,r=this.matrixWorld;s!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),Br.copy(n.boundingSphere),Br.applyMatrix4(r),Fi.copy(t.ray).recast(t.near),!(Br.containsPoint(Fi.origin)===!1&&(Fi.intersectSphere(Br,Ul)===null||Fi.origin.distanceToSquared(Ul)>(t.far-t.near)**2))&&(Il.copy(r).invert(),Fi.copy(t.ray).applyMatrix4(Il),!(n.boundingBox!==null&&Fi.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(t,e,Fi)))}_computeIntersections(t,e,n){let s;const r=this.geometry,a=this.material,o=r.index,c=r.attributes.position,l=r.attributes.uv,h=r.attributes.uv1,u=r.attributes.normal,f=r.groups,p=r.drawRange;if(o!==null)if(Array.isArray(a))for(let g=0,_=f.length;g<_;g++){const m=f[g],d=a[m.materialIndex],w=Math.max(m.start,p.start),T=Math.min(o.count,Math.min(m.start+m.count,p.start+p.count));for(let M=w,F=T;M<F;M+=3){const P=o.getX(M),N=o.getX(M+1),D=o.getX(M+2);s=Xr(this,d,t,n,l,h,u,P,N,D),s&&(s.faceIndex=Math.floor(M/3),s.face.materialIndex=m.materialIndex,e.push(s))}}else{const g=Math.max(0,p.start),_=Math.min(o.count,p.start+p.count);for(let m=g,d=_;m<d;m+=3){const w=o.getX(m),T=o.getX(m+1),M=o.getX(m+2);s=Xr(this,a,t,n,l,h,u,w,T,M),s&&(s.faceIndex=Math.floor(m/3),e.push(s))}}else if(c!==void 0)if(Array.isArray(a))for(let g=0,_=f.length;g<_;g++){const m=f[g],d=a[m.materialIndex],w=Math.max(m.start,p.start),T=Math.min(c.count,Math.min(m.start+m.count,p.start+p.count));for(let M=w,F=T;M<F;M+=3){const P=M,N=M+1,D=M+2;s=Xr(this,d,t,n,l,h,u,P,N,D),s&&(s.faceIndex=Math.floor(M/3),s.face.materialIndex=m.materialIndex,e.push(s))}}else{const g=Math.max(0,p.start),_=Math.min(c.count,p.start+p.count);for(let m=g,d=_;m<d;m+=3){const w=m,T=m+1,M=m+2;s=Xr(this,a,t,n,l,h,u,w,T,M),s&&(s.faceIndex=Math.floor(m/3),e.push(s))}}}}function Vf(i,t,e,n,s,r,a,o){let c;if(t.side===dn?c=n.intersectTriangle(a,r,s,!0,o):c=n.intersectTriangle(s,r,a,t.side===ai,o),c===null)return null;Wr.copy(o),Wr.applyMatrix4(i.matrixWorld);const l=e.ray.origin.distanceTo(Wr);return l<e.near||l>e.far?null:{distance:l,point:Wr.clone(),object:i}}function Xr(i,t,e,n,s,r,a,o,c,l){i.getVertexPosition(o,zr),i.getVertexPosition(c,Vr),i.getVertexPosition(l,Hr);const h=Vf(i,t,e,n,zr,Vr,Hr,Fl);if(h){const u=new L;Fn.getBarycoord(Fl,zr,Vr,Hr,u),s&&(h.uv=Fn.getInterpolatedAttribute(s,o,c,l,u,new At)),r&&(h.uv1=Fn.getInterpolatedAttribute(r,o,c,l,u,new At)),a&&(h.normal=Fn.getInterpolatedAttribute(a,o,c,l,u,new L),h.normal.dot(n.direction)>0&&h.normal.multiplyScalar(-1));const f={a:o,b:c,c:l,normal:new L,materialIndex:0};Fn.getNormal(zr,Vr,Hr,f.normal),h.face=f,h.barycoord=u}return h}class Os extends Pe{constructor(t=1,e=1,n=1,s=1,r=1,a=1){super(),this.type="BoxGeometry",this.parameters={width:t,height:e,depth:n,widthSegments:s,heightSegments:r,depthSegments:a};const o=this;s=Math.floor(s),r=Math.floor(r),a=Math.floor(a);const c=[],l=[],h=[],u=[];let f=0,p=0;g("z","y","x",-1,-1,n,e,t,a,r,0),g("z","y","x",1,-1,n,e,-t,a,r,1),g("x","z","y",1,1,t,n,e,s,a,2),g("x","z","y",1,-1,t,n,-e,s,a,3),g("x","y","z",1,-1,t,e,n,s,r,4),g("x","y","z",-1,-1,t,e,-n,s,r,5),this.setIndex(c),this.setAttribute("position",new ne(l,3)),this.setAttribute("normal",new ne(h,3)),this.setAttribute("uv",new ne(u,2));function g(_,m,d,w,T,M,F,P,N,D,y){const S=M/N,U=F/D,k=M/2,H=F/2,J=P/2,Q=N+1,O=D+1;let tt=0,W=0;const ct=new L;for(let ft=0;ft<O;ft++){const pt=ft*U-H;for(let Rt=0;Rt<Q;Rt++){const wt=Rt*S-k;ct[_]=wt*w,ct[m]=pt*T,ct[d]=J,l.push(ct.x,ct.y,ct.z),ct[_]=0,ct[m]=0,ct[d]=P>0?1:-1,h.push(ct.x,ct.y,ct.z),u.push(Rt/N),u.push(1-ft/D),tt+=1}}for(let ft=0;ft<D;ft++)for(let pt=0;pt<N;pt++){const Rt=f+pt+Q*ft,wt=f+pt+Q*(ft+1),X=f+(pt+1)+Q*(ft+1),K=f+(pt+1)+Q*ft;c.push(Rt,wt,K),c.push(wt,X,K),W+=6}o.addGroup(p,W,y),p+=W,f+=tt}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Os(t.width,t.height,t.depth,t.widthSegments,t.heightSegments,t.depthSegments)}}function Ls(i){const t={};for(const e in i){t[e]={};for(const n in i[e]){const s=i[e][n];s&&(s.isColor||s.isMatrix3||s.isMatrix4||s.isVector2||s.isVector3||s.isVector4||s.isTexture||s.isQuaternion)?s.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),t[e][n]=null):t[e][n]=s.clone():Array.isArray(s)?t[e][n]=s.slice():t[e][n]=s}}return t}function en(i){const t={};for(let e=0;e<i.length;e++){const n=Ls(i[e]);for(const s in n)t[s]=n[s]}return t}function Hf(i){const t=[];for(let e=0;e<i.length;e++)t.push(i[e].clone());return t}function mu(i){const t=i.getRenderTarget();return t===null?i.outputColorSpace:t.isXRRenderTarget===!0?t.texture.colorSpace:le.workingColorSpace}const Gf={clone:Ls,merge:en};var Wf=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,Xf=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class Ci extends Hn{static get type(){return"ShaderMaterial"}constructor(t){super(),this.isShaderMaterial=!0,this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=Wf,this.fragmentShader=Xf,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,t!==void 0&&this.setValues(t)}copy(t){return super.copy(t),this.fragmentShader=t.fragmentShader,this.vertexShader=t.vertexShader,this.uniforms=Ls(t.uniforms),this.uniformsGroups=Hf(t.uniformsGroups),this.defines=Object.assign({},t.defines),this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.fog=t.fog,this.lights=t.lights,this.clipping=t.clipping,this.extensions=Object.assign({},t.extensions),this.glslVersion=t.glslVersion,this}toJSON(t){const e=super.toJSON(t);e.glslVersion=this.glslVersion,e.uniforms={};for(const s in this.uniforms){const a=this.uniforms[s].value;a&&a.isTexture?e.uniforms[s]={type:"t",value:a.toJSON(t).uuid}:a&&a.isColor?e.uniforms[s]={type:"c",value:a.getHex()}:a&&a.isVector2?e.uniforms[s]={type:"v2",value:a.toArray()}:a&&a.isVector3?e.uniforms[s]={type:"v3",value:a.toArray()}:a&&a.isVector4?e.uniforms[s]={type:"v4",value:a.toArray()}:a&&a.isMatrix3?e.uniforms[s]={type:"m3",value:a.toArray()}:a&&a.isMatrix4?e.uniforms[s]={type:"m4",value:a.toArray()}:e.uniforms[s]={value:a}}Object.keys(this.defines).length>0&&(e.defines=this.defines),e.vertexShader=this.vertexShader,e.fragmentShader=this.fragmentShader,e.lights=this.lights,e.clipping=this.clipping;const n={};for(const s in this.extensions)this.extensions[s]===!0&&(n[s]=!0);return Object.keys(n).length>0&&(e.extensions=n),e}}class gu extends Ne{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new jt,this.projectionMatrix=new jt,this.projectionMatrixInverse=new jt,this.coordinateSystem=ri}copy(t,e){return super.copy(t,e),this.matrixWorldInverse.copy(t.matrixWorldInverse),this.projectionMatrix.copy(t.projectionMatrix),this.projectionMatrixInverse.copy(t.projectionMatrixInverse),this.coordinateSystem=t.coordinateSystem,this}getWorldDirection(t){return super.getWorldDirection(t).negate()}updateMatrixWorld(t){super.updateMatrixWorld(t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(t,e){super.updateWorldMatrix(t,e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}}const Mi=new L,Ol=new At,kl=new At;class Je extends gu{constructor(t=50,e=1,n=.1,s=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=t,this.zoom=1,this.near=n,this.far=s,this.focus=10,this.aspect=e,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.fov=t.fov,this.zoom=t.zoom,this.near=t.near,this.far=t.far,this.focus=t.focus,this.aspect=t.aspect,this.view=t.view===null?null:Object.assign({},t.view),this.filmGauge=t.filmGauge,this.filmOffset=t.filmOffset,this}setFocalLength(t){const e=.5*this.getFilmHeight()/t;this.fov=Ps*2*Math.atan(e),this.updateProjectionMatrix()}getFocalLength(){const t=Math.tan(ir*.5*this.fov);return .5*this.getFilmHeight()/t}getEffectiveFOV(){return Ps*2*Math.atan(Math.tan(ir*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(t,e,n){Mi.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),e.set(Mi.x,Mi.y).multiplyScalar(-t/Mi.z),Mi.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(Mi.x,Mi.y).multiplyScalar(-t/Mi.z)}getViewSize(t,e){return this.getViewBounds(t,Ol,kl),e.subVectors(kl,Ol)}setViewOffset(t,e,n,s,r,a){this.aspect=t/e,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=this.near;let e=t*Math.tan(ir*.5*this.fov)/this.zoom,n=2*e,s=this.aspect*n,r=-.5*s;const a=this.view;if(this.view!==null&&this.view.enabled){const c=a.fullWidth,l=a.fullHeight;r+=a.offsetX*s/c,e-=a.offsetY*n/l,s*=a.width/c,n*=a.height/l}const o=this.filmOffset;o!==0&&(r+=t*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+s,e,e-n,t,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.fov=this.fov,e.object.zoom=this.zoom,e.object.near=this.near,e.object.far=this.far,e.object.focus=this.focus,e.object.aspect=this.aspect,this.view!==null&&(e.object.view=Object.assign({},this.view)),e.object.filmGauge=this.filmGauge,e.object.filmOffset=this.filmOffset,e}}const hs=-90,us=1;class qf extends Ne{constructor(t,e,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;const s=new Je(hs,us,t,e);s.layers=this.layers,this.add(s);const r=new Je(hs,us,t,e);r.layers=this.layers,this.add(r);const a=new Je(hs,us,t,e);a.layers=this.layers,this.add(a);const o=new Je(hs,us,t,e);o.layers=this.layers,this.add(o);const c=new Je(hs,us,t,e);c.layers=this.layers,this.add(c);const l=new Je(hs,us,t,e);l.layers=this.layers,this.add(l)}updateCoordinateSystem(){const t=this.coordinateSystem,e=this.children.concat(),[n,s,r,a,o,c]=e;for(const l of e)this.remove(l);if(t===ri)n.up.set(0,1,0),n.lookAt(1,0,0),s.up.set(0,1,0),s.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),c.up.set(0,1,0),c.lookAt(0,0,-1);else if(t===yo)n.up.set(0,-1,0),n.lookAt(-1,0,0),s.up.set(0,-1,0),s.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),c.up.set(0,-1,0),c.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+t);for(const l of e)this.add(l),l.updateMatrixWorld()}update(t,e){this.parent===null&&this.updateMatrixWorld();const{renderTarget:n,activeMipmapLevel:s}=this;this.coordinateSystem!==t.coordinateSystem&&(this.coordinateSystem=t.coordinateSystem,this.updateCoordinateSystem());const[r,a,o,c,l,h]=this.children,u=t.getRenderTarget(),f=t.getActiveCubeFace(),p=t.getActiveMipmapLevel(),g=t.xr.enabled;t.xr.enabled=!1;const _=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,t.setRenderTarget(n,0,s),t.render(e,r),t.setRenderTarget(n,1,s),t.render(e,a),t.setRenderTarget(n,2,s),t.render(e,o),t.setRenderTarget(n,3,s),t.render(e,c),t.setRenderTarget(n,4,s),t.render(e,l),n.texture.generateMipmaps=_,t.setRenderTarget(n,5,s),t.render(e,h),t.setRenderTarget(u,f,p),t.xr.enabled=g,n.texture.needsPMREMUpdate=!0}}class _u extends Ye{constructor(t,e,n,s,r,a,o,c,l,h){t=t!==void 0?t:[],e=e!==void 0?e:Ts,super(t,e,n,s,r,a,o,c,l,h),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(t){this.image=t}}class jf extends qi{constructor(t=1,e={}){super(t,t,e),this.isWebGLCubeRenderTarget=!0;const n={width:t,height:t,depth:1},s=[n,n,n,n,n,n];this.texture=new _u(s,e.mapping,e.wrapS,e.wrapT,e.magFilter,e.minFilter,e.format,e.type,e.anisotropy,e.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.generateMipmaps=e.generateMipmaps!==void 0?e.generateMipmaps:!1,this.texture.minFilter=e.minFilter!==void 0?e.minFilter:_n}fromEquirectangularTexture(t,e){this.texture.type=e.type,this.texture.colorSpace=e.colorSpace,this.texture.generateMipmaps=e.generateMipmaps,this.texture.minFilter=e.minFilter,this.texture.magFilter=e.magFilter;const n={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},s=new Os(5,5,5),r=new Ci({name:"CubemapFromEquirect",uniforms:Ls(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:dn,blending:wi});r.uniforms.tEquirect.value=e;const a=new me(s,r),o=e.minFilter;return e.minFilter===si&&(e.minFilter=_n),new qf(1,10,this).update(t,a),e.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(t,e,n,s){const r=t.getRenderTarget();for(let a=0;a<6;a++)t.setRenderTarget(this,a),t.clear(e,n,s);t.setRenderTarget(r)}}const va=new L,Yf=new L,$f=new re;class ii{constructor(t=new L(1,0,0),e=0){this.isPlane=!0,this.normal=t,this.constant=e}set(t,e){return this.normal.copy(t),this.constant=e,this}setComponents(t,e,n,s){return this.normal.set(t,e,n),this.constant=s,this}setFromNormalAndCoplanarPoint(t,e){return this.normal.copy(t),this.constant=-e.dot(this.normal),this}setFromCoplanarPoints(t,e,n){const s=va.subVectors(n,e).cross(Yf.subVectors(t,e)).normalize();return this.setFromNormalAndCoplanarPoint(s,t),this}copy(t){return this.normal.copy(t.normal),this.constant=t.constant,this}normalize(){const t=1/this.normal.length();return this.normal.multiplyScalar(t),this.constant*=t,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(t){return this.normal.dot(t)+this.constant}distanceToSphere(t){return this.distanceToPoint(t.center)-t.radius}projectPoint(t,e){return e.copy(t).addScaledVector(this.normal,-this.distanceToPoint(t))}intersectLine(t,e){const n=t.delta(va),s=this.normal.dot(n);if(s===0)return this.distanceToPoint(t.start)===0?e.copy(t.start):null;const r=-(t.start.dot(this.normal)+this.constant)/s;return r<0||r>1?null:e.copy(t.start).addScaledVector(n,r)}intersectsLine(t){const e=this.distanceToPoint(t.start),n=this.distanceToPoint(t.end);return e<0&&n>0||n<0&&e>0}intersectsBox(t){return t.intersectsPlane(this)}intersectsSphere(t){return t.intersectsPlane(this)}coplanarPoint(t){return t.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(t,e){const n=e||$f.getNormalMatrix(t),s=this.coplanarPoint(va).applyMatrix4(t),r=this.normal.applyMatrix3(n).normalize();return this.constant=-s.dot(r),this}translate(t){return this.constant-=t.dot(this.normal),this}equals(t){return t.normal.equals(this.normal)&&t.constant===this.constant}clone(){return new this.constructor().copy(this)}}const Oi=new di,qr=new L;class Wc{constructor(t=new ii,e=new ii,n=new ii,s=new ii,r=new ii,a=new ii){this.planes=[t,e,n,s,r,a]}set(t,e,n,s,r,a){const o=this.planes;return o[0].copy(t),o[1].copy(e),o[2].copy(n),o[3].copy(s),o[4].copy(r),o[5].copy(a),this}copy(t){const e=this.planes;for(let n=0;n<6;n++)e[n].copy(t.planes[n]);return this}setFromProjectionMatrix(t,e=ri){const n=this.planes,s=t.elements,r=s[0],a=s[1],o=s[2],c=s[3],l=s[4],h=s[5],u=s[6],f=s[7],p=s[8],g=s[9],_=s[10],m=s[11],d=s[12],w=s[13],T=s[14],M=s[15];if(n[0].setComponents(c-r,f-l,m-p,M-d).normalize(),n[1].setComponents(c+r,f+l,m+p,M+d).normalize(),n[2].setComponents(c+a,f+h,m+g,M+w).normalize(),n[3].setComponents(c-a,f-h,m-g,M-w).normalize(),n[4].setComponents(c-o,f-u,m-_,M-T).normalize(),e===ri)n[5].setComponents(c+o,f+u,m+_,M+T).normalize();else if(e===yo)n[5].setComponents(o,u,_,T).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+e);return this}intersectsObject(t){if(t.boundingSphere!==void 0)t.boundingSphere===null&&t.computeBoundingSphere(),Oi.copy(t.boundingSphere).applyMatrix4(t.matrixWorld);else{const e=t.geometry;e.boundingSphere===null&&e.computeBoundingSphere(),Oi.copy(e.boundingSphere).applyMatrix4(t.matrixWorld)}return this.intersectsSphere(Oi)}intersectsSprite(t){return Oi.center.set(0,0,0),Oi.radius=.7071067811865476,Oi.applyMatrix4(t.matrixWorld),this.intersectsSphere(Oi)}intersectsSphere(t){const e=this.planes,n=t.center,s=-t.radius;for(let r=0;r<6;r++)if(e[r].distanceToPoint(n)<s)return!1;return!0}intersectsBox(t){const e=this.planes;for(let n=0;n<6;n++){const s=e[n];if(qr.x=s.normal.x>0?t.max.x:t.min.x,qr.y=s.normal.y>0?t.max.y:t.min.y,qr.z=s.normal.z>0?t.max.z:t.min.z,s.distanceToPoint(qr)<0)return!1}return!0}containsPoint(t){const e=this.planes;for(let n=0;n<6;n++)if(e[n].distanceToPoint(t)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}function vu(){let i=null,t=!1,e=null,n=null;function s(r,a){e(r,a),n=i.requestAnimationFrame(s)}return{start:function(){t!==!0&&e!==null&&(n=i.requestAnimationFrame(s),t=!0)},stop:function(){i.cancelAnimationFrame(n),t=!1},setAnimationLoop:function(r){e=r},setContext:function(r){i=r}}}function Kf(i){const t=new WeakMap;function e(o,c){const l=o.array,h=o.usage,u=l.byteLength,f=i.createBuffer();i.bindBuffer(c,f),i.bufferData(c,l,h),o.onUploadCallback();let p;if(l instanceof Float32Array)p=i.FLOAT;else if(l instanceof Uint16Array)o.isFloat16BufferAttribute?p=i.HALF_FLOAT:p=i.UNSIGNED_SHORT;else if(l instanceof Int16Array)p=i.SHORT;else if(l instanceof Uint32Array)p=i.UNSIGNED_INT;else if(l instanceof Int32Array)p=i.INT;else if(l instanceof Int8Array)p=i.BYTE;else if(l instanceof Uint8Array)p=i.UNSIGNED_BYTE;else if(l instanceof Uint8ClampedArray)p=i.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+l);return{buffer:f,type:p,bytesPerElement:l.BYTES_PER_ELEMENT,version:o.version,size:u}}function n(o,c,l){const h=c.array,u=c.updateRanges;if(i.bindBuffer(l,o),u.length===0)i.bufferSubData(l,0,h);else{u.sort((p,g)=>p.start-g.start);let f=0;for(let p=1;p<u.length;p++){const g=u[f],_=u[p];_.start<=g.start+g.count+1?g.count=Math.max(g.count,_.start+_.count-g.start):(++f,u[f]=_)}u.length=f+1;for(let p=0,g=u.length;p<g;p++){const _=u[p];i.bufferSubData(l,_.start*h.BYTES_PER_ELEMENT,h,_.start,_.count)}c.clearUpdateRanges()}c.onUploadCallback()}function s(o){return o.isInterleavedBufferAttribute&&(o=o.data),t.get(o)}function r(o){o.isInterleavedBufferAttribute&&(o=o.data);const c=t.get(o);c&&(i.deleteBuffer(c.buffer),t.delete(o))}function a(o,c){if(o.isInterleavedBufferAttribute&&(o=o.data),o.isGLBufferAttribute){const h=t.get(o);(!h||h.version<o.version)&&t.set(o,{buffer:o.buffer,type:o.type,bytesPerElement:o.elementSize,version:o.version});return}const l=t.get(o);if(l===void 0)t.set(o,e(o,c));else if(l.version<o.version){if(l.size!==o.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(l.buffer,o,c),l.version=o.version}}return{get:s,remove:r,update:a}}class Bo extends Pe{constructor(t=1,e=1,n=1,s=1){super(),this.type="PlaneGeometry",this.parameters={width:t,height:e,widthSegments:n,heightSegments:s};const r=t/2,a=e/2,o=Math.floor(n),c=Math.floor(s),l=o+1,h=c+1,u=t/o,f=e/c,p=[],g=[],_=[],m=[];for(let d=0;d<h;d++){const w=d*f-a;for(let T=0;T<l;T++){const M=T*u-r;g.push(M,-w,0),_.push(0,0,1),m.push(T/o),m.push(1-d/c)}}for(let d=0;d<c;d++)for(let w=0;w<o;w++){const T=w+l*d,M=w+l*(d+1),F=w+1+l*(d+1),P=w+1+l*d;p.push(T,M,P),p.push(M,F,P)}this.setIndex(p),this.setAttribute("position",new ne(g,3)),this.setAttribute("normal",new ne(_,3)),this.setAttribute("uv",new ne(m,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Bo(t.width,t.height,t.widthSegments,t.heightSegments)}}var Jf=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,Zf=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,Qf=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,tp=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,ep=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,np=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,ip=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,sp=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,rp=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`,op=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,ap=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,cp=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,lp=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,hp=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,up=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,dp=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,fp=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,pp=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,mp=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,gp=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,_p=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,vp=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,xp=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`,yp=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,Mp=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,Sp=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,bp=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Ep=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,wp=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,Tp=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Ap="gl_FragColor = linearToOutputTexel( gl_FragColor );",Cp=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,Rp=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,Pp=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Lp=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,Np=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,Dp=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,Ip=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,Up=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,Fp=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,Op=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,kp=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,Bp=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,zp=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,Vp=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,Hp=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,Gp=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,Wp=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,Xp=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,qp=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,jp=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,Yp=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,$p=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,Kp=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,Jp=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,Zp=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,Qp=`#if defined( USE_LOGDEPTHBUF )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,tm=`#if defined( USE_LOGDEPTHBUF )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,em=`#ifdef USE_LOGDEPTHBUF
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,nm=`#ifdef USE_LOGDEPTHBUF
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,im=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,sm=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,rm=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,om=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,am=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,cm=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,lm=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,hm=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,um=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,dm=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,fm=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,pm=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,mm=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,gm=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,_m=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,vm=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,xm=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,ym=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Mm=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Sm=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,bm=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Em=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,wm=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,Tm=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Am=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,Cm=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Rm=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,Pm=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Lm=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Nm=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		return step( compare, unpackRGBAToDepth( texture2D( depths, uv ) ) );
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow (sampler2D shadow, vec2 uv, float compare ){
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		float hard_shadow = step( compare , distribution.x );
		if (hard_shadow != 1.0 ) {
			float distance = compare - distribution.x ;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`,Dm=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,Im=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,Um=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,Fm=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,Om=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,km=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,Bm=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,zm=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,Vm=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,Hm=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,Gm=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,Wm=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,Xm=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
		
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
		
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		
		#else
		
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,qm=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,jm=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,Ym=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,$m=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const Km=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,Jm=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Zm=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Qm=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,tg=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,eg=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,ng=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,ig=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	float fragCoordZ = 0.5 * vHighPrecisionZW[0] / vHighPrecisionZW[1] + 0.5;
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,sg=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,rg=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,og=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,ag=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,cg=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,lg=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,hg=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,ug=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,dg=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,fg=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,pg=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,mg=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,gg=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,_g=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,vg=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,xg=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,yg=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,Mg=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Sg=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,bg=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,Eg=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,wg=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,Tg=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,Ag=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Cg=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,Rg=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,oe={alphahash_fragment:Jf,alphahash_pars_fragment:Zf,alphamap_fragment:Qf,alphamap_pars_fragment:tp,alphatest_fragment:ep,alphatest_pars_fragment:np,aomap_fragment:ip,aomap_pars_fragment:sp,batching_pars_vertex:rp,batching_vertex:op,begin_vertex:ap,beginnormal_vertex:cp,bsdfs:lp,iridescence_fragment:hp,bumpmap_pars_fragment:up,clipping_planes_fragment:dp,clipping_planes_pars_fragment:fp,clipping_planes_pars_vertex:pp,clipping_planes_vertex:mp,color_fragment:gp,color_pars_fragment:_p,color_pars_vertex:vp,color_vertex:xp,common:yp,cube_uv_reflection_fragment:Mp,defaultnormal_vertex:Sp,displacementmap_pars_vertex:bp,displacementmap_vertex:Ep,emissivemap_fragment:wp,emissivemap_pars_fragment:Tp,colorspace_fragment:Ap,colorspace_pars_fragment:Cp,envmap_fragment:Rp,envmap_common_pars_fragment:Pp,envmap_pars_fragment:Lp,envmap_pars_vertex:Np,envmap_physical_pars_fragment:Gp,envmap_vertex:Dp,fog_vertex:Ip,fog_pars_vertex:Up,fog_fragment:Fp,fog_pars_fragment:Op,gradientmap_pars_fragment:kp,lightmap_pars_fragment:Bp,lights_lambert_fragment:zp,lights_lambert_pars_fragment:Vp,lights_pars_begin:Hp,lights_toon_fragment:Wp,lights_toon_pars_fragment:Xp,lights_phong_fragment:qp,lights_phong_pars_fragment:jp,lights_physical_fragment:Yp,lights_physical_pars_fragment:$p,lights_fragment_begin:Kp,lights_fragment_maps:Jp,lights_fragment_end:Zp,logdepthbuf_fragment:Qp,logdepthbuf_pars_fragment:tm,logdepthbuf_pars_vertex:em,logdepthbuf_vertex:nm,map_fragment:im,map_pars_fragment:sm,map_particle_fragment:rm,map_particle_pars_fragment:om,metalnessmap_fragment:am,metalnessmap_pars_fragment:cm,morphinstance_vertex:lm,morphcolor_vertex:hm,morphnormal_vertex:um,morphtarget_pars_vertex:dm,morphtarget_vertex:fm,normal_fragment_begin:pm,normal_fragment_maps:mm,normal_pars_fragment:gm,normal_pars_vertex:_m,normal_vertex:vm,normalmap_pars_fragment:xm,clearcoat_normal_fragment_begin:ym,clearcoat_normal_fragment_maps:Mm,clearcoat_pars_fragment:Sm,iridescence_pars_fragment:bm,opaque_fragment:Em,packing:wm,premultiplied_alpha_fragment:Tm,project_vertex:Am,dithering_fragment:Cm,dithering_pars_fragment:Rm,roughnessmap_fragment:Pm,roughnessmap_pars_fragment:Lm,shadowmap_pars_fragment:Nm,shadowmap_pars_vertex:Dm,shadowmap_vertex:Im,shadowmask_pars_fragment:Um,skinbase_vertex:Fm,skinning_pars_vertex:Om,skinning_vertex:km,skinnormal_vertex:Bm,specularmap_fragment:zm,specularmap_pars_fragment:Vm,tonemapping_fragment:Hm,tonemapping_pars_fragment:Gm,transmission_fragment:Wm,transmission_pars_fragment:Xm,uv_pars_fragment:qm,uv_pars_vertex:jm,uv_vertex:Ym,worldpos_vertex:$m,background_vert:Km,background_frag:Jm,backgroundCube_vert:Zm,backgroundCube_frag:Qm,cube_vert:tg,cube_frag:eg,depth_vert:ng,depth_frag:ig,distanceRGBA_vert:sg,distanceRGBA_frag:rg,equirect_vert:og,equirect_frag:ag,linedashed_vert:cg,linedashed_frag:lg,meshbasic_vert:hg,meshbasic_frag:ug,meshlambert_vert:dg,meshlambert_frag:fg,meshmatcap_vert:pg,meshmatcap_frag:mg,meshnormal_vert:gg,meshnormal_frag:_g,meshphong_vert:vg,meshphong_frag:xg,meshphysical_vert:yg,meshphysical_frag:Mg,meshtoon_vert:Sg,meshtoon_frag:bg,points_vert:Eg,points_frag:wg,shadow_vert:Tg,shadow_frag:Ag,sprite_vert:Cg,sprite_frag:Rg},_t={common:{diffuse:{value:new Kt(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new re},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new re}},envmap:{envMap:{value:null},envMapRotation:{value:new re},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new re}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new re}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new re},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new re},normalScale:{value:new At(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new re},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new re}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new re}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new re}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Kt(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new Kt(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0},uvTransform:{value:new re}},sprite:{diffuse:{value:new Kt(16777215)},opacity:{value:1},center:{value:new At(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new re},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0}}},Gn={basic:{uniforms:en([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.fog]),vertexShader:oe.meshbasic_vert,fragmentShader:oe.meshbasic_frag},lambert:{uniforms:en([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,_t.lights,{emissive:{value:new Kt(0)}}]),vertexShader:oe.meshlambert_vert,fragmentShader:oe.meshlambert_frag},phong:{uniforms:en([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,_t.lights,{emissive:{value:new Kt(0)},specular:{value:new Kt(1118481)},shininess:{value:30}}]),vertexShader:oe.meshphong_vert,fragmentShader:oe.meshphong_frag},standard:{uniforms:en([_t.common,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.roughnessmap,_t.metalnessmap,_t.fog,_t.lights,{emissive:{value:new Kt(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:oe.meshphysical_vert,fragmentShader:oe.meshphysical_frag},toon:{uniforms:en([_t.common,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.gradientmap,_t.fog,_t.lights,{emissive:{value:new Kt(0)}}]),vertexShader:oe.meshtoon_vert,fragmentShader:oe.meshtoon_frag},matcap:{uniforms:en([_t.common,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,{matcap:{value:null}}]),vertexShader:oe.meshmatcap_vert,fragmentShader:oe.meshmatcap_frag},points:{uniforms:en([_t.points,_t.fog]),vertexShader:oe.points_vert,fragmentShader:oe.points_frag},dashed:{uniforms:en([_t.common,_t.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:oe.linedashed_vert,fragmentShader:oe.linedashed_frag},depth:{uniforms:en([_t.common,_t.displacementmap]),vertexShader:oe.depth_vert,fragmentShader:oe.depth_frag},normal:{uniforms:en([_t.common,_t.bumpmap,_t.normalmap,_t.displacementmap,{opacity:{value:1}}]),vertexShader:oe.meshnormal_vert,fragmentShader:oe.meshnormal_frag},sprite:{uniforms:en([_t.sprite,_t.fog]),vertexShader:oe.sprite_vert,fragmentShader:oe.sprite_frag},background:{uniforms:{uvTransform:{value:new re},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:oe.background_vert,fragmentShader:oe.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new re}},vertexShader:oe.backgroundCube_vert,fragmentShader:oe.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:oe.cube_vert,fragmentShader:oe.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:oe.equirect_vert,fragmentShader:oe.equirect_frag},distanceRGBA:{uniforms:en([_t.common,_t.displacementmap,{referencePosition:{value:new L},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:oe.distanceRGBA_vert,fragmentShader:oe.distanceRGBA_frag},shadow:{uniforms:en([_t.lights,_t.fog,{color:{value:new Kt(0)},opacity:{value:1}}]),vertexShader:oe.shadow_vert,fragmentShader:oe.shadow_frag}};Gn.physical={uniforms:en([Gn.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new re},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new re},clearcoatNormalScale:{value:new At(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new re},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new re},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new re},sheen:{value:0},sheenColor:{value:new Kt(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new re},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new re},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new re},transmissionSamplerSize:{value:new At},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new re},attenuationDistance:{value:0},attenuationColor:{value:new Kt(0)},specularColor:{value:new Kt(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new re},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new re},anisotropyVector:{value:new At},anisotropyMap:{value:null},anisotropyMapTransform:{value:new re}}]),vertexShader:oe.meshphysical_vert,fragmentShader:oe.meshphysical_frag};const jr={r:0,b:0,g:0},ki=new fn,Pg=new jt;function Lg(i,t,e,n,s,r,a){const o=new Kt(0);let c=r===!0?0:1,l,h,u=null,f=0,p=null;function g(w){let T=w.isScene===!0?w.background:null;return T&&T.isTexture&&(T=(w.backgroundBlurriness>0?e:t).get(T)),T}function _(w){let T=!1;const M=g(w);M===null?d(o,c):M&&M.isColor&&(d(M,1),T=!0);const F=i.xr.getEnvironmentBlendMode();F==="additive"?n.buffers.color.setClear(0,0,0,1,a):F==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,a),(i.autoClear||T)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),i.clear(i.autoClearColor,i.autoClearDepth,i.autoClearStencil))}function m(w,T){const M=g(T);M&&(M.isCubeTexture||M.mapping===Fo)?(h===void 0&&(h=new me(new Os(1,1,1),new Ci({name:"BackgroundCubeMaterial",uniforms:Ls(Gn.backgroundCube.uniforms),vertexShader:Gn.backgroundCube.vertexShader,fragmentShader:Gn.backgroundCube.fragmentShader,side:dn,depthTest:!1,depthWrite:!1,fog:!1})),h.geometry.deleteAttribute("normal"),h.geometry.deleteAttribute("uv"),h.onBeforeRender=function(F,P,N){this.matrixWorld.copyPosition(N.matrixWorld)},Object.defineProperty(h.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),s.update(h)),ki.copy(T.backgroundRotation),ki.x*=-1,ki.y*=-1,ki.z*=-1,M.isCubeTexture&&M.isRenderTargetTexture===!1&&(ki.y*=-1,ki.z*=-1),h.material.uniforms.envMap.value=M,h.material.uniforms.flipEnvMap.value=M.isCubeTexture&&M.isRenderTargetTexture===!1?-1:1,h.material.uniforms.backgroundBlurriness.value=T.backgroundBlurriness,h.material.uniforms.backgroundIntensity.value=T.backgroundIntensity,h.material.uniforms.backgroundRotation.value.setFromMatrix4(Pg.makeRotationFromEuler(ki)),h.material.toneMapped=le.getTransfer(M.colorSpace)!==Ee,(u!==M||f!==M.version||p!==i.toneMapping)&&(h.material.needsUpdate=!0,u=M,f=M.version,p=i.toneMapping),h.layers.enableAll(),w.unshift(h,h.geometry,h.material,0,0,null)):M&&M.isTexture&&(l===void 0&&(l=new me(new Bo(2,2),new Ci({name:"BackgroundMaterial",uniforms:Ls(Gn.background.uniforms),vertexShader:Gn.background.vertexShader,fragmentShader:Gn.background.fragmentShader,side:ai,depthTest:!1,depthWrite:!1,fog:!1})),l.geometry.deleteAttribute("normal"),Object.defineProperty(l.material,"map",{get:function(){return this.uniforms.t2D.value}}),s.update(l)),l.material.uniforms.t2D.value=M,l.material.uniforms.backgroundIntensity.value=T.backgroundIntensity,l.material.toneMapped=le.getTransfer(M.colorSpace)!==Ee,M.matrixAutoUpdate===!0&&M.updateMatrix(),l.material.uniforms.uvTransform.value.copy(M.matrix),(u!==M||f!==M.version||p!==i.toneMapping)&&(l.material.needsUpdate=!0,u=M,f=M.version,p=i.toneMapping),l.layers.enableAll(),w.unshift(l,l.geometry,l.material,0,0,null))}function d(w,T){w.getRGB(jr,mu(i)),n.buffers.color.setClear(jr.r,jr.g,jr.b,T,a)}return{getClearColor:function(){return o},setClearColor:function(w,T=1){o.set(w),c=T,d(o,c)},getClearAlpha:function(){return c},setClearAlpha:function(w){c=w,d(o,c)},render:_,addToRenderList:m}}function Ng(i,t){const e=i.getParameter(i.MAX_VERTEX_ATTRIBS),n={},s=f(null);let r=s,a=!1;function o(S,U,k,H,J){let Q=!1;const O=u(H,k,U);r!==O&&(r=O,l(r.object)),Q=p(S,H,k,J),Q&&g(S,H,k,J),J!==null&&t.update(J,i.ELEMENT_ARRAY_BUFFER),(Q||a)&&(a=!1,M(S,U,k,H),J!==null&&i.bindBuffer(i.ELEMENT_ARRAY_BUFFER,t.get(J).buffer))}function c(){return i.createVertexArray()}function l(S){return i.bindVertexArray(S)}function h(S){return i.deleteVertexArray(S)}function u(S,U,k){const H=k.wireframe===!0;let J=n[S.id];J===void 0&&(J={},n[S.id]=J);let Q=J[U.id];Q===void 0&&(Q={},J[U.id]=Q);let O=Q[H];return O===void 0&&(O=f(c()),Q[H]=O),O}function f(S){const U=[],k=[],H=[];for(let J=0;J<e;J++)U[J]=0,k[J]=0,H[J]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:U,enabledAttributes:k,attributeDivisors:H,object:S,attributes:{},index:null}}function p(S,U,k,H){const J=r.attributes,Q=U.attributes;let O=0;const tt=k.getAttributes();for(const W in tt)if(tt[W].location>=0){const ft=J[W];let pt=Q[W];if(pt===void 0&&(W==="instanceMatrix"&&S.instanceMatrix&&(pt=S.instanceMatrix),W==="instanceColor"&&S.instanceColor&&(pt=S.instanceColor)),ft===void 0||ft.attribute!==pt||pt&&ft.data!==pt.data)return!0;O++}return r.attributesNum!==O||r.index!==H}function g(S,U,k,H){const J={},Q=U.attributes;let O=0;const tt=k.getAttributes();for(const W in tt)if(tt[W].location>=0){let ft=Q[W];ft===void 0&&(W==="instanceMatrix"&&S.instanceMatrix&&(ft=S.instanceMatrix),W==="instanceColor"&&S.instanceColor&&(ft=S.instanceColor));const pt={};pt.attribute=ft,ft&&ft.data&&(pt.data=ft.data),J[W]=pt,O++}r.attributes=J,r.attributesNum=O,r.index=H}function _(){const S=r.newAttributes;for(let U=0,k=S.length;U<k;U++)S[U]=0}function m(S){d(S,0)}function d(S,U){const k=r.newAttributes,H=r.enabledAttributes,J=r.attributeDivisors;k[S]=1,H[S]===0&&(i.enableVertexAttribArray(S),H[S]=1),J[S]!==U&&(i.vertexAttribDivisor(S,U),J[S]=U)}function w(){const S=r.newAttributes,U=r.enabledAttributes;for(let k=0,H=U.length;k<H;k++)U[k]!==S[k]&&(i.disableVertexAttribArray(k),U[k]=0)}function T(S,U,k,H,J,Q,O){O===!0?i.vertexAttribIPointer(S,U,k,J,Q):i.vertexAttribPointer(S,U,k,H,J,Q)}function M(S,U,k,H){_();const J=H.attributes,Q=k.getAttributes(),O=U.defaultAttributeValues;for(const tt in Q){const W=Q[tt];if(W.location>=0){let ct=J[tt];if(ct===void 0&&(tt==="instanceMatrix"&&S.instanceMatrix&&(ct=S.instanceMatrix),tt==="instanceColor"&&S.instanceColor&&(ct=S.instanceColor)),ct!==void 0){const ft=ct.normalized,pt=ct.itemSize,Rt=t.get(ct);if(Rt===void 0)continue;const wt=Rt.buffer,X=Rt.type,K=Rt.bytesPerElement,nt=X===i.INT||X===i.UNSIGNED_INT||ct.gpuType===Fc;if(ct.isInterleavedBufferAttribute){const it=ct.data,vt=it.stride,zt=ct.offset;if(it.isInstancedInterleavedBuffer){for(let Zt=0;Zt<W.locationSize;Zt++)d(W.location+Zt,it.meshPerAttribute);S.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=it.meshPerAttribute*it.count)}else for(let Zt=0;Zt<W.locationSize;Zt++)m(W.location+Zt);i.bindBuffer(i.ARRAY_BUFFER,wt);for(let Zt=0;Zt<W.locationSize;Zt++)T(W.location+Zt,pt/W.locationSize,X,ft,vt*K,(zt+pt/W.locationSize*Zt)*K,nt)}else{if(ct.isInstancedBufferAttribute){for(let it=0;it<W.locationSize;it++)d(W.location+it,ct.meshPerAttribute);S.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=ct.meshPerAttribute*ct.count)}else for(let it=0;it<W.locationSize;it++)m(W.location+it);i.bindBuffer(i.ARRAY_BUFFER,wt);for(let it=0;it<W.locationSize;it++)T(W.location+it,pt/W.locationSize,X,ft,pt*K,pt/W.locationSize*it*K,nt)}}else if(O!==void 0){const ft=O[tt];if(ft!==void 0)switch(ft.length){case 2:i.vertexAttrib2fv(W.location,ft);break;case 3:i.vertexAttrib3fv(W.location,ft);break;case 4:i.vertexAttrib4fv(W.location,ft);break;default:i.vertexAttrib1fv(W.location,ft)}}}}w()}function F(){D();for(const S in n){const U=n[S];for(const k in U){const H=U[k];for(const J in H)h(H[J].object),delete H[J];delete U[k]}delete n[S]}}function P(S){if(n[S.id]===void 0)return;const U=n[S.id];for(const k in U){const H=U[k];for(const J in H)h(H[J].object),delete H[J];delete U[k]}delete n[S.id]}function N(S){for(const U in n){const k=n[U];if(k[S.id]===void 0)continue;const H=k[S.id];for(const J in H)h(H[J].object),delete H[J];delete k[S.id]}}function D(){y(),a=!0,r!==s&&(r=s,l(r.object))}function y(){s.geometry=null,s.program=null,s.wireframe=!1}return{setup:o,reset:D,resetDefaultState:y,dispose:F,releaseStatesOfGeometry:P,releaseStatesOfProgram:N,initAttributes:_,enableAttribute:m,disableUnusedAttributes:w}}function Dg(i,t,e){let n;function s(l){n=l}function r(l,h){i.drawArrays(n,l,h),e.update(h,n,1)}function a(l,h,u){u!==0&&(i.drawArraysInstanced(n,l,h,u),e.update(h,n,u))}function o(l,h,u){if(u===0)return;t.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,l,0,h,0,u);let p=0;for(let g=0;g<u;g++)p+=h[g];e.update(p,n,1)}function c(l,h,u,f){if(u===0)return;const p=t.get("WEBGL_multi_draw");if(p===null)for(let g=0;g<l.length;g++)a(l[g],h[g],f[g]);else{p.multiDrawArraysInstancedWEBGL(n,l,0,h,0,f,0,u);let g=0;for(let _=0;_<u;_++)g+=h[_]*f[_];e.update(g,n,1)}}this.setMode=s,this.render=r,this.renderInstances=a,this.renderMultiDraw=o,this.renderMultiDrawInstances=c}function Ig(i,t,e,n){let s;function r(){if(s!==void 0)return s;if(t.has("EXT_texture_filter_anisotropic")===!0){const N=t.get("EXT_texture_filter_anisotropic");s=i.getParameter(N.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else s=0;return s}function a(N){return!(N!==wn&&n.convert(N)!==i.getParameter(i.IMPLEMENTATION_COLOR_READ_FORMAT))}function o(N){const D=N===gr&&(t.has("EXT_color_buffer_half_float")||t.has("EXT_color_buffer_float"));return!(N!==ci&&n.convert(N)!==i.getParameter(i.IMPLEMENTATION_COLOR_READ_TYPE)&&N!==Wn&&!D)}function c(N){if(N==="highp"){if(i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.HIGH_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.HIGH_FLOAT).precision>0)return"highp";N="mediump"}return N==="mediump"&&i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.MEDIUM_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let l=e.precision!==void 0?e.precision:"highp";const h=c(l);h!==l&&(console.warn("THREE.WebGLRenderer:",l,"not supported, using",h,"instead."),l=h);const u=e.logarithmicDepthBuffer===!0,f=e.reverseDepthBuffer===!0&&t.has("EXT_clip_control"),p=i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS),g=i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS),_=i.getParameter(i.MAX_TEXTURE_SIZE),m=i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE),d=i.getParameter(i.MAX_VERTEX_ATTRIBS),w=i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS),T=i.getParameter(i.MAX_VARYING_VECTORS),M=i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS),F=g>0,P=i.getParameter(i.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:c,textureFormatReadable:a,textureTypeReadable:o,precision:l,logarithmicDepthBuffer:u,reverseDepthBuffer:f,maxTextures:p,maxVertexTextures:g,maxTextureSize:_,maxCubemapSize:m,maxAttributes:d,maxVertexUniforms:w,maxVaryings:T,maxFragmentUniforms:M,vertexTextures:F,maxSamples:P}}function Ug(i){const t=this;let e=null,n=0,s=!1,r=!1;const a=new ii,o=new re,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(u,f){const p=u.length!==0||f||n!==0||s;return s=f,n=u.length,p},this.beginShadows=function(){r=!0,h(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(u,f){e=h(u,f,0)},this.setState=function(u,f,p){const g=u.clippingPlanes,_=u.clipIntersection,m=u.clipShadows,d=i.get(u);if(!s||g===null||g.length===0||r&&!m)r?h(null):l();else{const w=r?0:n,T=w*4;let M=d.clippingState||null;c.value=M,M=h(g,f,T,p);for(let F=0;F!==T;++F)M[F]=e[F];d.clippingState=M,this.numIntersection=_?this.numPlanes:0,this.numPlanes+=w}};function l(){c.value!==e&&(c.value=e,c.needsUpdate=n>0),t.numPlanes=n,t.numIntersection=0}function h(u,f,p,g){const _=u!==null?u.length:0;let m=null;if(_!==0){if(m=c.value,g!==!0||m===null){const d=p+_*4,w=f.matrixWorldInverse;o.getNormalMatrix(w),(m===null||m.length<d)&&(m=new Float32Array(d));for(let T=0,M=p;T!==_;++T,M+=4)a.copy(u[T]).applyMatrix4(w,o),a.normal.toArray(m,M),m[M+3]=a.constant}c.value=m,c.needsUpdate=!0}return t.numPlanes=_,t.numIntersection=0,m}}function Fg(i){let t=new WeakMap;function e(a,o){return o===Ka?a.mapping=Ts:o===Ja&&(a.mapping=As),a}function n(a){if(a&&a.isTexture){const o=a.mapping;if(o===Ka||o===Ja)if(t.has(a)){const c=t.get(a).texture;return e(c,a.mapping)}else{const c=a.image;if(c&&c.height>0){const l=new jf(c.height);return l.fromEquirectangularTexture(i,a),t.set(a,l),a.addEventListener("dispose",s),e(l.texture,a.mapping)}else return null}}return a}function s(a){const o=a.target;o.removeEventListener("dispose",s);const c=t.get(o);c!==void 0&&(t.delete(o),c.dispose())}function r(){t=new WeakMap}return{get:n,dispose:r}}class Xc extends gu{constructor(t=-1,e=1,n=1,s=-1,r=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=t,this.right=e,this.top=n,this.bottom=s,this.near=r,this.far=a,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.left=t.left,this.right=t.right,this.top=t.top,this.bottom=t.bottom,this.near=t.near,this.far=t.far,this.zoom=t.zoom,this.view=t.view===null?null:Object.assign({},t.view),this}setViewOffset(t,e,n,s,r,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=(this.right-this.left)/(2*this.zoom),e=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,s=(this.top+this.bottom)/2;let r=n-t,a=n+t,o=s+e,c=s-e;if(this.view!==null&&this.view.enabled){const l=(this.right-this.left)/this.view.fullWidth/this.zoom,h=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=l*this.view.offsetX,a=r+l*this.view.width,o-=h*this.view.offsetY,c=o-h*this.view.height}this.projectionMatrix.makeOrthographic(r,a,o,c,this.near,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.zoom=this.zoom,e.object.left=this.left,e.object.right=this.right,e.object.top=this.top,e.object.bottom=this.bottom,e.object.near=this.near,e.object.far=this.far,this.view!==null&&(e.object.view=Object.assign({},this.view)),e}}const gs=4,Bl=[.125,.215,.35,.446,.526,.582],Gi=20,xa=new Xc,zl=new Kt;let ya=null,Ma=0,Sa=0,ba=!1;const Vi=(1+Math.sqrt(5))/2,ds=1/Vi,Vl=[new L(-Vi,ds,0),new L(Vi,ds,0),new L(-ds,0,Vi),new L(ds,0,Vi),new L(0,Vi,-ds),new L(0,Vi,ds),new L(-1,1,-1),new L(1,1,-1),new L(-1,1,1),new L(1,1,1)];class Hl{constructor(t){this._renderer=t,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(t,e=0,n=.1,s=100){ya=this._renderer.getRenderTarget(),Ma=this._renderer.getActiveCubeFace(),Sa=this._renderer.getActiveMipmapLevel(),ba=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(256);const r=this._allocateTargets();return r.depthBuffer=!0,this._sceneToCubeUV(t,n,s,r),e>0&&this._blur(r,0,0,e),this._applyPMREM(r),this._cleanup(r),r}fromEquirectangular(t,e=null){return this._fromTexture(t,e)}fromCubemap(t,e=null){return this._fromTexture(t,e)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Xl(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Wl(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(t){this._lodMax=Math.floor(Math.log2(t)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let t=0;t<this._lodPlanes.length;t++)this._lodPlanes[t].dispose()}_cleanup(t){this._renderer.setRenderTarget(ya,Ma,Sa),this._renderer.xr.enabled=ba,t.scissorTest=!1,Yr(t,0,0,t.width,t.height)}_fromTexture(t,e){t.mapping===Ts||t.mapping===As?this._setSize(t.image.length===0?16:t.image[0].width||t.image[0].image.width):this._setSize(t.image.width/4),ya=this._renderer.getRenderTarget(),Ma=this._renderer.getActiveCubeFace(),Sa=this._renderer.getActiveMipmapLevel(),ba=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;const n=e||this._allocateTargets();return this._textureToCubeUV(t,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){const t=3*Math.max(this._cubeSize,112),e=4*this._cubeSize,n={magFilter:_n,minFilter:_n,generateMipmaps:!1,type:gr,format:wn,colorSpace:Us,depthBuffer:!1},s=Gl(t,e,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==t||this._pingPongRenderTarget.height!==e){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Gl(t,e,n);const{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=Og(r)),this._blurMaterial=kg(r,t,e)}return s}_compileMaterial(t){const e=new me(this._lodPlanes[0],t);this._renderer.compile(e,xa)}_sceneToCubeUV(t,e,n,s){const o=new Je(90,1,e,n),c=[1,-1,1,1,1,1],l=[1,1,1,-1,-1,-1],h=this._renderer,u=h.autoClear,f=h.toneMapping;h.getClearColor(zl),h.toneMapping=Ti,h.autoClear=!1;const p=new je({name:"PMREM.Background",side:dn,depthWrite:!1,depthTest:!1}),g=new me(new Os,p);let _=!1;const m=t.background;m?m.isColor&&(p.color.copy(m),t.background=null,_=!0):(p.color.copy(zl),_=!0);for(let d=0;d<6;d++){const w=d%3;w===0?(o.up.set(0,c[d],0),o.lookAt(l[d],0,0)):w===1?(o.up.set(0,0,c[d]),o.lookAt(0,l[d],0)):(o.up.set(0,c[d],0),o.lookAt(0,0,l[d]));const T=this._cubeSize;Yr(s,w*T,d>2?T:0,T,T),h.setRenderTarget(s),_&&h.render(g,o),h.render(t,o)}g.geometry.dispose(),g.material.dispose(),h.toneMapping=f,h.autoClear=u,t.background=m}_textureToCubeUV(t,e){const n=this._renderer,s=t.mapping===Ts||t.mapping===As;s?(this._cubemapMaterial===null&&(this._cubemapMaterial=Xl()),this._cubemapMaterial.uniforms.flipEnvMap.value=t.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Wl());const r=s?this._cubemapMaterial:this._equirectMaterial,a=new me(this._lodPlanes[0],r),o=r.uniforms;o.envMap.value=t;const c=this._cubeSize;Yr(e,0,0,3*c,2*c),n.setRenderTarget(e),n.render(a,xa)}_applyPMREM(t){const e=this._renderer,n=e.autoClear;e.autoClear=!1;const s=this._lodPlanes.length;for(let r=1;r<s;r++){const a=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),o=Vl[(s-r-1)%Vl.length];this._blur(t,r-1,r,a,o)}e.autoClear=n}_blur(t,e,n,s,r){const a=this._pingPongRenderTarget;this._halfBlur(t,a,e,n,s,"latitudinal",r),this._halfBlur(a,t,n,n,s,"longitudinal",r)}_halfBlur(t,e,n,s,r,a,o){const c=this._renderer,l=this._blurMaterial;a!=="latitudinal"&&a!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");const h=3,u=new me(this._lodPlanes[s],l),f=l.uniforms,p=this._sizeLods[n]-1,g=isFinite(r)?Math.PI/(2*p):2*Math.PI/(2*Gi-1),_=r/g,m=isFinite(r)?1+Math.floor(h*_):Gi;m>Gi&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${Gi}`);const d=[];let w=0;for(let N=0;N<Gi;++N){const D=N/_,y=Math.exp(-D*D/2);d.push(y),N===0?w+=y:N<m&&(w+=2*y)}for(let N=0;N<d.length;N++)d[N]=d[N]/w;f.envMap.value=t.texture,f.samples.value=m,f.weights.value=d,f.latitudinal.value=a==="latitudinal",o&&(f.poleAxis.value=o);const{_lodMax:T}=this;f.dTheta.value=g,f.mipInt.value=T-n;const M=this._sizeLods[s],F=3*M*(s>T-gs?s-T+gs:0),P=4*(this._cubeSize-M);Yr(e,F,P,3*M,2*M),c.setRenderTarget(e),c.render(u,xa)}}function Og(i){const t=[],e=[],n=[];let s=i;const r=i-gs+1+Bl.length;for(let a=0;a<r;a++){const o=Math.pow(2,s);e.push(o);let c=1/o;a>i-gs?c=Bl[a-i+gs-1]:a===0&&(c=0),n.push(c);const l=1/(o-2),h=-l,u=1+l,f=[h,h,u,h,u,u,h,h,u,u,h,u],p=6,g=6,_=3,m=2,d=1,w=new Float32Array(_*g*p),T=new Float32Array(m*g*p),M=new Float32Array(d*g*p);for(let P=0;P<p;P++){const N=P%3*2/3-1,D=P>2?0:-1,y=[N,D,0,N+2/3,D,0,N+2/3,D+1,0,N,D,0,N+2/3,D+1,0,N,D+1,0];w.set(y,_*g*P),T.set(f,m*g*P);const S=[P,P,P,P,P,P];M.set(S,d*g*P)}const F=new Pe;F.setAttribute("position",new xn(w,_)),F.setAttribute("uv",new xn(T,m)),F.setAttribute("faceIndex",new xn(M,d)),t.push(F),s>gs&&s--}return{lodPlanes:t,sizeLods:e,sigmas:n}}function Gl(i,t,e){const n=new qi(i,t,e);return n.texture.mapping=Fo,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function Yr(i,t,e,n,s){i.viewport.set(t,e,n,s),i.scissor.set(t,e,n,s)}function kg(i,t,e){const n=new Float32Array(Gi),s=new L(0,1,0);return new Ci({name:"SphericalGaussianBlur",defines:{n:Gi,CUBEUV_TEXEL_WIDTH:1/t,CUBEUV_TEXEL_HEIGHT:1/e,CUBEUV_MAX_MIP:`${i}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:s}},vertexShader:qc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:wi,depthTest:!1,depthWrite:!1})}function Wl(){return new Ci({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:qc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:wi,depthTest:!1,depthWrite:!1})}function Xl(){return new Ci({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:qc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:wi,depthTest:!1,depthWrite:!1})}function qc(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function Bg(i){let t=new WeakMap,e=null;function n(o){if(o&&o.isTexture){const c=o.mapping,l=c===Ka||c===Ja,h=c===Ts||c===As;if(l||h){let u=t.get(o);const f=u!==void 0?u.texture.pmremVersion:0;if(o.isRenderTargetTexture&&o.pmremVersion!==f)return e===null&&(e=new Hl(i)),u=l?e.fromEquirectangular(o,u):e.fromCubemap(o,u),u.texture.pmremVersion=o.pmremVersion,t.set(o,u),u.texture;if(u!==void 0)return u.texture;{const p=o.image;return l&&p&&p.height>0||h&&p&&s(p)?(e===null&&(e=new Hl(i)),u=l?e.fromEquirectangular(o):e.fromCubemap(o),u.texture.pmremVersion=o.pmremVersion,t.set(o,u),o.addEventListener("dispose",r),u.texture):null}}}return o}function s(o){let c=0;const l=6;for(let h=0;h<l;h++)o[h]!==void 0&&c++;return c===l}function r(o){const c=o.target;c.removeEventListener("dispose",r);const l=t.get(c);l!==void 0&&(t.delete(c),l.dispose())}function a(){t=new WeakMap,e!==null&&(e.dispose(),e=null)}return{get:n,dispose:a}}function zg(i){const t={};function e(n){if(t[n]!==void 0)return t[n];let s;switch(n){case"WEBGL_depth_texture":s=i.getExtension("WEBGL_depth_texture")||i.getExtension("MOZ_WEBGL_depth_texture")||i.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":s=i.getExtension("EXT_texture_filter_anisotropic")||i.getExtension("MOZ_EXT_texture_filter_anisotropic")||i.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":s=i.getExtension("WEBGL_compressed_texture_s3tc")||i.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":s=i.getExtension("WEBGL_compressed_texture_pvrtc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:s=i.getExtension(n)}return t[n]=s,s}return{has:function(n){return e(n)!==null},init:function(){e("EXT_color_buffer_float"),e("WEBGL_clip_cull_distance"),e("OES_texture_float_linear"),e("EXT_color_buffer_half_float"),e("WEBGL_multisampled_render_to_texture"),e("WEBGL_render_shared_exponent")},get:function(n){const s=e(n);return s===null&&Zs("THREE.WebGLRenderer: "+n+" extension not supported."),s}}}function Vg(i,t,e,n){const s={},r=new WeakMap;function a(u){const f=u.target;f.index!==null&&t.remove(f.index);for(const g in f.attributes)t.remove(f.attributes[g]);for(const g in f.morphAttributes){const _=f.morphAttributes[g];for(let m=0,d=_.length;m<d;m++)t.remove(_[m])}f.removeEventListener("dispose",a),delete s[f.id];const p=r.get(f);p&&(t.remove(p),r.delete(f)),n.releaseStatesOfGeometry(f),f.isInstancedBufferGeometry===!0&&delete f._maxInstanceCount,e.memory.geometries--}function o(u,f){return s[f.id]===!0||(f.addEventListener("dispose",a),s[f.id]=!0,e.memory.geometries++),f}function c(u){const f=u.attributes;for(const g in f)t.update(f[g],i.ARRAY_BUFFER);const p=u.morphAttributes;for(const g in p){const _=p[g];for(let m=0,d=_.length;m<d;m++)t.update(_[m],i.ARRAY_BUFFER)}}function l(u){const f=[],p=u.index,g=u.attributes.position;let _=0;if(p!==null){const w=p.array;_=p.version;for(let T=0,M=w.length;T<M;T+=3){const F=w[T+0],P=w[T+1],N=w[T+2];f.push(F,P,P,N,N,F)}}else if(g!==void 0){const w=g.array;_=g.version;for(let T=0,M=w.length/3-1;T<M;T+=3){const F=T+0,P=T+1,N=T+2;f.push(F,P,P,N,N,F)}}else return;const m=new(lu(f)?pu:fu)(f,1);m.version=_;const d=r.get(u);d&&t.remove(d),r.set(u,m)}function h(u){const f=r.get(u);if(f){const p=u.index;p!==null&&f.version<p.version&&l(u)}else l(u);return r.get(u)}return{get:o,update:c,getWireframeAttribute:h}}function Hg(i,t,e){let n;function s(f){n=f}let r,a;function o(f){r=f.type,a=f.bytesPerElement}function c(f,p){i.drawElements(n,p,r,f*a),e.update(p,n,1)}function l(f,p,g){g!==0&&(i.drawElementsInstanced(n,p,r,f*a,g),e.update(p,n,g))}function h(f,p,g){if(g===0)return;t.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,p,0,r,f,0,g);let m=0;for(let d=0;d<g;d++)m+=p[d];e.update(m,n,1)}function u(f,p,g,_){if(g===0)return;const m=t.get("WEBGL_multi_draw");if(m===null)for(let d=0;d<f.length;d++)l(f[d]/a,p[d],_[d]);else{m.multiDrawElementsInstancedWEBGL(n,p,0,r,f,0,_,0,g);let d=0;for(let w=0;w<g;w++)d+=p[w]*_[w];e.update(d,n,1)}}this.setMode=s,this.setIndex=o,this.render=c,this.renderInstances=l,this.renderMultiDraw=h,this.renderMultiDrawInstances=u}function Gg(i){const t={geometries:0,textures:0},e={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,a,o){switch(e.calls++,a){case i.TRIANGLES:e.triangles+=o*(r/3);break;case i.LINES:e.lines+=o*(r/2);break;case i.LINE_STRIP:e.lines+=o*(r-1);break;case i.LINE_LOOP:e.lines+=o*r;break;case i.POINTS:e.points+=o*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",a);break}}function s(){e.calls=0,e.triangles=0,e.points=0,e.lines=0}return{memory:t,render:e,programs:null,autoReset:!0,reset:s,update:n}}function Wg(i,t,e){const n=new WeakMap,s=new xe;function r(a,o,c){const l=a.morphTargetInfluences,h=o.morphAttributes.position||o.morphAttributes.normal||o.morphAttributes.color,u=h!==void 0?h.length:0;let f=n.get(o);if(f===void 0||f.count!==u){let S=function(){D.dispose(),n.delete(o),o.removeEventListener("dispose",S)};var p=S;f!==void 0&&f.texture.dispose();const g=o.morphAttributes.position!==void 0,_=o.morphAttributes.normal!==void 0,m=o.morphAttributes.color!==void 0,d=o.morphAttributes.position||[],w=o.morphAttributes.normal||[],T=o.morphAttributes.color||[];let M=0;g===!0&&(M=1),_===!0&&(M=2),m===!0&&(M=3);let F=o.attributes.position.count*M,P=1;F>t.maxTextureSize&&(P=Math.ceil(F/t.maxTextureSize),F=t.maxTextureSize);const N=new Float32Array(F*P*4*u),D=new uu(N,F,P,u);D.type=Wn,D.needsUpdate=!0;const y=M*4;for(let U=0;U<u;U++){const k=d[U],H=w[U],J=T[U],Q=F*P*4*U;for(let O=0;O<k.count;O++){const tt=O*y;g===!0&&(s.fromBufferAttribute(k,O),N[Q+tt+0]=s.x,N[Q+tt+1]=s.y,N[Q+tt+2]=s.z,N[Q+tt+3]=0),_===!0&&(s.fromBufferAttribute(H,O),N[Q+tt+4]=s.x,N[Q+tt+5]=s.y,N[Q+tt+6]=s.z,N[Q+tt+7]=0),m===!0&&(s.fromBufferAttribute(J,O),N[Q+tt+8]=s.x,N[Q+tt+9]=s.y,N[Q+tt+10]=s.z,N[Q+tt+11]=J.itemSize===4?s.w:1)}}f={count:u,texture:D,size:new At(F,P)},n.set(o,f),o.addEventListener("dispose",S)}if(a.isInstancedMesh===!0&&a.morphTexture!==null)c.getUniforms().setValue(i,"morphTexture",a.morphTexture,e);else{let g=0;for(let m=0;m<l.length;m++)g+=l[m];const _=o.morphTargetsRelative?1:1-g;c.getUniforms().setValue(i,"morphTargetBaseInfluence",_),c.getUniforms().setValue(i,"morphTargetInfluences",l)}c.getUniforms().setValue(i,"morphTargetsTexture",f.texture,e),c.getUniforms().setValue(i,"morphTargetsTextureSize",f.size)}return{update:r}}function Xg(i,t,e,n){let s=new WeakMap;function r(c){const l=n.render.frame,h=c.geometry,u=t.get(c,h);if(s.get(u)!==l&&(t.update(u),s.set(u,l)),c.isInstancedMesh&&(c.hasEventListener("dispose",o)===!1&&c.addEventListener("dispose",o),s.get(c)!==l&&(e.update(c.instanceMatrix,i.ARRAY_BUFFER),c.instanceColor!==null&&e.update(c.instanceColor,i.ARRAY_BUFFER),s.set(c,l))),c.isSkinnedMesh){const f=c.skeleton;s.get(f)!==l&&(f.update(),s.set(f,l))}return u}function a(){s=new WeakMap}function o(c){const l=c.target;l.removeEventListener("dispose",o),e.remove(l.instanceMatrix),l.instanceColor!==null&&e.remove(l.instanceColor)}return{update:r,dispose:a}}class xu extends Ye{constructor(t,e,n,s,r,a,o,c,l,h=xs){if(h!==xs&&h!==Rs)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");n===void 0&&h===xs&&(n=Xi),n===void 0&&h===Rs&&(n=Cs),super(null,s,r,a,o,c,h,n,l),this.isDepthTexture=!0,this.image={width:t,height:e},this.magFilter=o!==void 0?o:vn,this.minFilter=c!==void 0?c:vn,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(t){return super.copy(t),this.compareFunction=t.compareFunction,this}toJSON(t){const e=super.toJSON(t);return this.compareFunction!==null&&(e.compareFunction=this.compareFunction),e}}const yu=new Ye,ql=new xu(1,1),Mu=new uu,Su=new Lf,bu=new _u,jl=[],Yl=[],$l=new Float32Array(16),Kl=new Float32Array(9),Jl=new Float32Array(4);function ks(i,t,e){const n=i[0];if(n<=0||n>0)return i;const s=t*e;let r=jl[s];if(r===void 0&&(r=new Float32Array(s),jl[s]=r),t!==0){n.toArray(r,0);for(let a=1,o=0;a!==t;++a)o+=e,i[a].toArray(r,o)}return r}function He(i,t){if(i.length!==t.length)return!1;for(let e=0,n=i.length;e<n;e++)if(i[e]!==t[e])return!1;return!0}function Ge(i,t){for(let e=0,n=t.length;e<n;e++)i[e]=t[e]}function zo(i,t){let e=Yl[t];e===void 0&&(e=new Int32Array(t),Yl[t]=e);for(let n=0;n!==t;++n)e[n]=i.allocateTextureUnit();return e}function qg(i,t){const e=this.cache;e[0]!==t&&(i.uniform1f(this.addr,t),e[0]=t)}function jg(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2f(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(He(e,t))return;i.uniform2fv(this.addr,t),Ge(e,t)}}function Yg(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3f(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else if(t.r!==void 0)(e[0]!==t.r||e[1]!==t.g||e[2]!==t.b)&&(i.uniform3f(this.addr,t.r,t.g,t.b),e[0]=t.r,e[1]=t.g,e[2]=t.b);else{if(He(e,t))return;i.uniform3fv(this.addr,t),Ge(e,t)}}function $g(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4f(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(He(e,t))return;i.uniform4fv(this.addr,t),Ge(e,t)}}function Kg(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(He(e,t))return;i.uniformMatrix2fv(this.addr,!1,t),Ge(e,t)}else{if(He(e,n))return;Jl.set(n),i.uniformMatrix2fv(this.addr,!1,Jl),Ge(e,n)}}function Jg(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(He(e,t))return;i.uniformMatrix3fv(this.addr,!1,t),Ge(e,t)}else{if(He(e,n))return;Kl.set(n),i.uniformMatrix3fv(this.addr,!1,Kl),Ge(e,n)}}function Zg(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(He(e,t))return;i.uniformMatrix4fv(this.addr,!1,t),Ge(e,t)}else{if(He(e,n))return;$l.set(n),i.uniformMatrix4fv(this.addr,!1,$l),Ge(e,n)}}function Qg(i,t){const e=this.cache;e[0]!==t&&(i.uniform1i(this.addr,t),e[0]=t)}function t_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2i(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(He(e,t))return;i.uniform2iv(this.addr,t),Ge(e,t)}}function e_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3i(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(He(e,t))return;i.uniform3iv(this.addr,t),Ge(e,t)}}function n_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4i(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(He(e,t))return;i.uniform4iv(this.addr,t),Ge(e,t)}}function i_(i,t){const e=this.cache;e[0]!==t&&(i.uniform1ui(this.addr,t),e[0]=t)}function s_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2ui(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(He(e,t))return;i.uniform2uiv(this.addr,t),Ge(e,t)}}function r_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3ui(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(He(e,t))return;i.uniform3uiv(this.addr,t),Ge(e,t)}}function o_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4ui(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(He(e,t))return;i.uniform4uiv(this.addr,t),Ge(e,t)}}function a_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s);let r;this.type===i.SAMPLER_2D_SHADOW?(ql.compareFunction=cu,r=ql):r=yu,e.setTexture2D(t||r,s)}function c_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTexture3D(t||Su,s)}function l_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTextureCube(t||bu,s)}function h_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTexture2DArray(t||Mu,s)}function u_(i){switch(i){case 5126:return qg;case 35664:return jg;case 35665:return Yg;case 35666:return $g;case 35674:return Kg;case 35675:return Jg;case 35676:return Zg;case 5124:case 35670:return Qg;case 35667:case 35671:return t_;case 35668:case 35672:return e_;case 35669:case 35673:return n_;case 5125:return i_;case 36294:return s_;case 36295:return r_;case 36296:return o_;case 35678:case 36198:case 36298:case 36306:case 35682:return a_;case 35679:case 36299:case 36307:return c_;case 35680:case 36300:case 36308:case 36293:return l_;case 36289:case 36303:case 36311:case 36292:return h_}}function d_(i,t){i.uniform1fv(this.addr,t)}function f_(i,t){const e=ks(t,this.size,2);i.uniform2fv(this.addr,e)}function p_(i,t){const e=ks(t,this.size,3);i.uniform3fv(this.addr,e)}function m_(i,t){const e=ks(t,this.size,4);i.uniform4fv(this.addr,e)}function g_(i,t){const e=ks(t,this.size,4);i.uniformMatrix2fv(this.addr,!1,e)}function __(i,t){const e=ks(t,this.size,9);i.uniformMatrix3fv(this.addr,!1,e)}function v_(i,t){const e=ks(t,this.size,16);i.uniformMatrix4fv(this.addr,!1,e)}function x_(i,t){i.uniform1iv(this.addr,t)}function y_(i,t){i.uniform2iv(this.addr,t)}function M_(i,t){i.uniform3iv(this.addr,t)}function S_(i,t){i.uniform4iv(this.addr,t)}function b_(i,t){i.uniform1uiv(this.addr,t)}function E_(i,t){i.uniform2uiv(this.addr,t)}function w_(i,t){i.uniform3uiv(this.addr,t)}function T_(i,t){i.uniform4uiv(this.addr,t)}function A_(i,t,e){const n=this.cache,s=t.length,r=zo(e,s);He(n,r)||(i.uniform1iv(this.addr,r),Ge(n,r));for(let a=0;a!==s;++a)e.setTexture2D(t[a]||yu,r[a])}function C_(i,t,e){const n=this.cache,s=t.length,r=zo(e,s);He(n,r)||(i.uniform1iv(this.addr,r),Ge(n,r));for(let a=0;a!==s;++a)e.setTexture3D(t[a]||Su,r[a])}function R_(i,t,e){const n=this.cache,s=t.length,r=zo(e,s);He(n,r)||(i.uniform1iv(this.addr,r),Ge(n,r));for(let a=0;a!==s;++a)e.setTextureCube(t[a]||bu,r[a])}function P_(i,t,e){const n=this.cache,s=t.length,r=zo(e,s);He(n,r)||(i.uniform1iv(this.addr,r),Ge(n,r));for(let a=0;a!==s;++a)e.setTexture2DArray(t[a]||Mu,r[a])}function L_(i){switch(i){case 5126:return d_;case 35664:return f_;case 35665:return p_;case 35666:return m_;case 35674:return g_;case 35675:return __;case 35676:return v_;case 5124:case 35670:return x_;case 35667:case 35671:return y_;case 35668:case 35672:return M_;case 35669:case 35673:return S_;case 5125:return b_;case 36294:return E_;case 36295:return w_;case 36296:return T_;case 35678:case 36198:case 36298:case 36306:case 35682:return A_;case 35679:case 36299:case 36307:return C_;case 35680:case 36300:case 36308:case 36293:return R_;case 36289:case 36303:case 36311:case 36292:return P_}}class N_{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.setValue=u_(e.type)}}class D_{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.size=e.size,this.setValue=L_(e.type)}}class I_{constructor(t){this.id=t,this.seq=[],this.map={}}setValue(t,e,n){const s=this.seq;for(let r=0,a=s.length;r!==a;++r){const o=s[r];o.setValue(t,e[o.id],n)}}}const Ea=/(\w+)(\])?(\[|\.)?/g;function Zl(i,t){i.seq.push(t),i.map[t.id]=t}function U_(i,t,e){const n=i.name,s=n.length;for(Ea.lastIndex=0;;){const r=Ea.exec(n),a=Ea.lastIndex;let o=r[1];const c=r[2]==="]",l=r[3];if(c&&(o=o|0),l===void 0||l==="["&&a+2===s){Zl(e,l===void 0?new N_(o,i,t):new D_(o,i,t));break}else{let u=e.map[o];u===void 0&&(u=new I_(o),Zl(e,u)),e=u}}}class go{constructor(t,e){this.seq=[],this.map={};const n=t.getProgramParameter(e,t.ACTIVE_UNIFORMS);for(let s=0;s<n;++s){const r=t.getActiveUniform(e,s),a=t.getUniformLocation(e,r.name);U_(r,a,this)}}setValue(t,e,n,s){const r=this.map[e];r!==void 0&&r.setValue(t,n,s)}setOptional(t,e,n){const s=e[n];s!==void 0&&this.setValue(t,n,s)}static upload(t,e,n,s){for(let r=0,a=e.length;r!==a;++r){const o=e[r],c=n[o.id];c.needsUpdate!==!1&&o.setValue(t,c.value,s)}}static seqWithValue(t,e){const n=[];for(let s=0,r=t.length;s!==r;++s){const a=t[s];a.id in e&&n.push(a)}return n}}function Ql(i,t,e){const n=i.createShader(t);return i.shaderSource(n,e),i.compileShader(n),n}const F_=37297;let O_=0;function k_(i,t){const e=i.split(`
`),n=[],s=Math.max(t-6,0),r=Math.min(t+6,e.length);for(let a=s;a<r;a++){const o=a+1;n.push(`${o===t?">":" "} ${o}: ${e[a]}`)}return n.join(`
`)}const th=new re;function B_(i){le._getMatrix(th,le.workingColorSpace,i);const t=`mat3( ${th.elements.map(e=>e.toFixed(4))} )`;switch(le.getTransfer(i)){case ko:return[t,"LinearTransferOETF"];case Ee:return[t,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",i),[t,"LinearTransferOETF"]}}function eh(i,t,e){const n=i.getShaderParameter(t,i.COMPILE_STATUS),s=i.getShaderInfoLog(t).trim();if(n&&s==="")return"";const r=/ERROR: 0:(\d+)/.exec(s);if(r){const a=parseInt(r[1]);return e.toUpperCase()+`

`+s+`

`+k_(i.getShaderSource(t),a)}else return s}function z_(i,t){const e=B_(t);return[`vec4 ${i}( vec4 value ) {`,`	return ${e[1]}( vec4( value.rgb * ${e[0]}, value.a ) );`,"}"].join(`
`)}function V_(i,t){let e;switch(t){case Vd:e="Linear";break;case Hd:e="Reinhard";break;case Gd:e="Cineon";break;case Kh:e="ACESFilmic";break;case Xd:e="AgX";break;case qd:e="Neutral";break;case Wd:e="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",t),e="Linear"}return"vec3 "+i+"( vec3 color ) { return "+e+"ToneMapping( color ); }"}const $r=new L;function H_(){le.getLuminanceCoefficients($r);const i=$r.x.toFixed(4),t=$r.y.toFixed(4),e=$r.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${i}, ${t}, ${e} );`,"	return dot( weights, rgb );","}"].join(`
`)}function G_(i){return[i.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",i.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Qs).join(`
`)}function W_(i){const t=[];for(const e in i){const n=i[e];n!==!1&&t.push("#define "+e+" "+n)}return t.join(`
`)}function X_(i,t){const e={},n=i.getProgramParameter(t,i.ACTIVE_ATTRIBUTES);for(let s=0;s<n;s++){const r=i.getActiveAttrib(t,s),a=r.name;let o=1;r.type===i.FLOAT_MAT2&&(o=2),r.type===i.FLOAT_MAT3&&(o=3),r.type===i.FLOAT_MAT4&&(o=4),e[a]={type:r.type,location:i.getAttribLocation(t,a),locationSize:o}}return e}function Qs(i){return i!==""}function nh(i,t){const e=t.numSpotLightShadows+t.numSpotLightMaps-t.numSpotLightShadowsWithMaps;return i.replace(/NUM_DIR_LIGHTS/g,t.numDirLights).replace(/NUM_SPOT_LIGHTS/g,t.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,t.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,e).replace(/NUM_RECT_AREA_LIGHTS/g,t.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,t.numPointLights).replace(/NUM_HEMI_LIGHTS/g,t.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,t.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,t.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,t.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,t.numPointLightShadows)}function ih(i,t){return i.replace(/NUM_CLIPPING_PLANES/g,t.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,t.numClippingPlanes-t.numClipIntersection)}const q_=/^[ \t]*#include +<([\w\d./]+)>/gm;function Tc(i){return i.replace(q_,Y_)}const j_=new Map;function Y_(i,t){let e=oe[t];if(e===void 0){const n=j_.get(t);if(n!==void 0)e=oe[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',t,n);else throw new Error("Can not resolve #include <"+t+">")}return Tc(e)}const $_=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function sh(i){return i.replace($_,K_)}function K_(i,t,e,n){let s="";for(let r=parseInt(t);r<parseInt(e);r++)s+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return s}function rh(i){let t=`precision ${i.precision} float;
	precision ${i.precision} int;
	precision ${i.precision} sampler2D;
	precision ${i.precision} samplerCube;
	precision ${i.precision} sampler3D;
	precision ${i.precision} sampler2DArray;
	precision ${i.precision} sampler2DShadow;
	precision ${i.precision} samplerCubeShadow;
	precision ${i.precision} sampler2DArrayShadow;
	precision ${i.precision} isampler2D;
	precision ${i.precision} isampler3D;
	precision ${i.precision} isamplerCube;
	precision ${i.precision} isampler2DArray;
	precision ${i.precision} usampler2D;
	precision ${i.precision} usampler3D;
	precision ${i.precision} usamplerCube;
	precision ${i.precision} usampler2DArray;
	`;return i.precision==="highp"?t+=`
#define HIGH_PRECISION`:i.precision==="mediump"?t+=`
#define MEDIUM_PRECISION`:i.precision==="lowp"&&(t+=`
#define LOW_PRECISION`),t}function J_(i){let t="SHADOWMAP_TYPE_BASIC";return i.shadowMapType===$h?t="SHADOWMAP_TYPE_PCF":i.shadowMapType===yd?t="SHADOWMAP_TYPE_PCF_SOFT":i.shadowMapType===ni&&(t="SHADOWMAP_TYPE_VSM"),t}function Z_(i){let t="ENVMAP_TYPE_CUBE";if(i.envMap)switch(i.envMapMode){case Ts:case As:t="ENVMAP_TYPE_CUBE";break;case Fo:t="ENVMAP_TYPE_CUBE_UV";break}return t}function Q_(i){let t="ENVMAP_MODE_REFLECTION";if(i.envMap)switch(i.envMapMode){case As:t="ENVMAP_MODE_REFRACTION";break}return t}function t0(i){let t="ENVMAP_BLENDING_NONE";if(i.envMap)switch(i.combine){case Uo:t="ENVMAP_BLENDING_MULTIPLY";break;case Bd:t="ENVMAP_BLENDING_MIX";break;case zd:t="ENVMAP_BLENDING_ADD";break}return t}function e0(i){const t=i.envMapCubeUVHeight;if(t===null)return null;const e=Math.log2(t)-2,n=1/t;return{texelWidth:1/(3*Math.max(Math.pow(2,e),112)),texelHeight:n,maxMip:e}}function n0(i,t,e,n){const s=i.getContext(),r=e.defines;let a=e.vertexShader,o=e.fragmentShader;const c=J_(e),l=Z_(e),h=Q_(e),u=t0(e),f=e0(e),p=G_(e),g=W_(r),_=s.createProgram();let m,d,w=e.glslVersion?"#version "+e.glslVersion+`
`:"";e.isRawShaderMaterial?(m=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(Qs).join(`
`),m.length>0&&(m+=`
`),d=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(Qs).join(`
`),d.length>0&&(d+=`
`)):(m=[rh(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",e.batching?"#define USE_BATCHING":"",e.batchingColor?"#define USE_BATCHING_COLOR":"",e.instancing?"#define USE_INSTANCING":"",e.instancingColor?"#define USE_INSTANCING_COLOR":"",e.instancingMorph?"#define USE_INSTANCING_MORPH":"",e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.map?"#define USE_MAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+h:"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.displacementMap?"#define USE_DISPLACEMENTMAP":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.mapUv?"#define MAP_UV "+e.mapUv:"",e.alphaMapUv?"#define ALPHAMAP_UV "+e.alphaMapUv:"",e.lightMapUv?"#define LIGHTMAP_UV "+e.lightMapUv:"",e.aoMapUv?"#define AOMAP_UV "+e.aoMapUv:"",e.emissiveMapUv?"#define EMISSIVEMAP_UV "+e.emissiveMapUv:"",e.bumpMapUv?"#define BUMPMAP_UV "+e.bumpMapUv:"",e.normalMapUv?"#define NORMALMAP_UV "+e.normalMapUv:"",e.displacementMapUv?"#define DISPLACEMENTMAP_UV "+e.displacementMapUv:"",e.metalnessMapUv?"#define METALNESSMAP_UV "+e.metalnessMapUv:"",e.roughnessMapUv?"#define ROUGHNESSMAP_UV "+e.roughnessMapUv:"",e.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+e.anisotropyMapUv:"",e.clearcoatMapUv?"#define CLEARCOATMAP_UV "+e.clearcoatMapUv:"",e.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+e.clearcoatNormalMapUv:"",e.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+e.clearcoatRoughnessMapUv:"",e.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+e.iridescenceMapUv:"",e.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+e.iridescenceThicknessMapUv:"",e.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+e.sheenColorMapUv:"",e.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+e.sheenRoughnessMapUv:"",e.specularMapUv?"#define SPECULARMAP_UV "+e.specularMapUv:"",e.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+e.specularColorMapUv:"",e.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+e.specularIntensityMapUv:"",e.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+e.transmissionMapUv:"",e.thicknessMapUv?"#define THICKNESSMAP_UV "+e.thicknessMapUv:"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.flatShading?"#define FLAT_SHADED":"",e.skinning?"#define USE_SKINNING":"",e.morphTargets?"#define USE_MORPHTARGETS":"",e.morphNormals&&e.flatShading===!1?"#define USE_MORPHNORMALS":"",e.morphColors?"#define USE_MORPHCOLORS":"",e.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+e.morphTextureStride:"",e.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+e.morphTargetsCount:"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+c:"",e.sizeAttenuation?"#define USE_SIZEATTENUATION":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Qs).join(`
`),d=[rh(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",e.map?"#define USE_MAP":"",e.matcap?"#define USE_MATCAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+l:"",e.envMap?"#define "+h:"",e.envMap?"#define "+u:"",f?"#define CUBEUV_TEXEL_WIDTH "+f.texelWidth:"",f?"#define CUBEUV_TEXEL_HEIGHT "+f.texelHeight:"",f?"#define CUBEUV_MAX_MIP "+f.maxMip+".0":"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoat?"#define USE_CLEARCOAT":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.dispersion?"#define USE_DISPERSION":"",e.iridescence?"#define USE_IRIDESCENCE":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaTest?"#define USE_ALPHATEST":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.sheen?"#define USE_SHEEN":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors||e.instancingColor||e.batchingColor?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.gradientMap?"#define USE_GRADIENTMAP":"",e.flatShading?"#define FLAT_SHADED":"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+c:"",e.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",e.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",e.toneMapping!==Ti?"#define TONE_MAPPING":"",e.toneMapping!==Ti?oe.tonemapping_pars_fragment:"",e.toneMapping!==Ti?V_("toneMapping",e.toneMapping):"",e.dithering?"#define DITHERING":"",e.opaque?"#define OPAQUE":"",oe.colorspace_pars_fragment,z_("linearToOutputTexel",e.outputColorSpace),H_(),e.useDepthPacking?"#define DEPTH_PACKING "+e.depthPacking:"",`
`].filter(Qs).join(`
`)),a=Tc(a),a=nh(a,e),a=ih(a,e),o=Tc(o),o=nh(o,e),o=ih(o,e),a=sh(a),o=sh(o),e.isRawShaderMaterial!==!0&&(w=`#version 300 es
`,m=[p,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+m,d=["#define varying in",e.glslVersion===_l?"":"layout(location = 0) out highp vec4 pc_fragColor;",e.glslVersion===_l?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+d);const T=w+m+a,M=w+d+o,F=Ql(s,s.VERTEX_SHADER,T),P=Ql(s,s.FRAGMENT_SHADER,M);s.attachShader(_,F),s.attachShader(_,P),e.index0AttributeName!==void 0?s.bindAttribLocation(_,0,e.index0AttributeName):e.morphTargets===!0&&s.bindAttribLocation(_,0,"position"),s.linkProgram(_);function N(U){if(i.debug.checkShaderErrors){const k=s.getProgramInfoLog(_).trim(),H=s.getShaderInfoLog(F).trim(),J=s.getShaderInfoLog(P).trim();let Q=!0,O=!0;if(s.getProgramParameter(_,s.LINK_STATUS)===!1)if(Q=!1,typeof i.debug.onShaderError=="function")i.debug.onShaderError(s,_,F,P);else{const tt=eh(s,F,"vertex"),W=eh(s,P,"fragment");console.error("THREE.WebGLProgram: Shader Error "+s.getError()+" - VALIDATE_STATUS "+s.getProgramParameter(_,s.VALIDATE_STATUS)+`

Material Name: `+U.name+`
Material Type: `+U.type+`

Program Info Log: `+k+`
`+tt+`
`+W)}else k!==""?console.warn("THREE.WebGLProgram: Program Info Log:",k):(H===""||J==="")&&(O=!1);O&&(U.diagnostics={runnable:Q,programLog:k,vertexShader:{log:H,prefix:m},fragmentShader:{log:J,prefix:d}})}s.deleteShader(F),s.deleteShader(P),D=new go(s,_),y=X_(s,_)}let D;this.getUniforms=function(){return D===void 0&&N(this),D};let y;this.getAttributes=function(){return y===void 0&&N(this),y};let S=e.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return S===!1&&(S=s.getProgramParameter(_,F_)),S},this.destroy=function(){n.releaseStatesOfProgram(this),s.deleteProgram(_),this.program=void 0},this.type=e.shaderType,this.name=e.shaderName,this.id=O_++,this.cacheKey=t,this.usedTimes=1,this.program=_,this.vertexShader=F,this.fragmentShader=P,this}let i0=0;class s0{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(t){const e=t.vertexShader,n=t.fragmentShader,s=this._getShaderStage(e),r=this._getShaderStage(n),a=this._getShaderCacheForMaterial(t);return a.has(s)===!1&&(a.add(s),s.usedTimes++),a.has(r)===!1&&(a.add(r),r.usedTimes++),this}remove(t){const e=this.materialCache.get(t);for(const n of e)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(t),this}getVertexShaderID(t){return this._getShaderStage(t.vertexShader).id}getFragmentShaderID(t){return this._getShaderStage(t.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(t){const e=this.materialCache;let n=e.get(t);return n===void 0&&(n=new Set,e.set(t,n)),n}_getShaderStage(t){const e=this.shaderCache;let n=e.get(t);return n===void 0&&(n=new r0(t),e.set(t,n)),n}}class r0{constructor(t){this.id=i0++,this.code=t,this.usedTimes=0}}function o0(i,t,e,n,s,r,a){const o=new Gc,c=new s0,l=new Set,h=[],u=s.logarithmicDepthBuffer,f=s.vertexTextures;let p=s.precision;const g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function _(y){return l.add(y),y===0?"uv":`uv${y}`}function m(y,S,U,k,H){const J=k.fog,Q=H.geometry,O=y.isMeshStandardMaterial?k.environment:null,tt=(y.isMeshStandardMaterial?e:t).get(y.envMap||O),W=tt&&tt.mapping===Fo?tt.image.height:null,ct=g[y.type];y.precision!==null&&(p=s.getMaxPrecision(y.precision),p!==y.precision&&console.warn("THREE.WebGLProgram.getParameters:",y.precision,"not supported, using",p,"instead."));const ft=Q.morphAttributes.position||Q.morphAttributes.normal||Q.morphAttributes.color,pt=ft!==void 0?ft.length:0;let Rt=0;Q.morphAttributes.position!==void 0&&(Rt=1),Q.morphAttributes.normal!==void 0&&(Rt=2),Q.morphAttributes.color!==void 0&&(Rt=3);let wt,X,K,nt;if(ct){const ie=Gn[ct];wt=ie.vertexShader,X=ie.fragmentShader}else wt=y.vertexShader,X=y.fragmentShader,c.update(y),K=c.getVertexShaderID(y),nt=c.getFragmentShaderID(y);const it=i.getRenderTarget(),vt=i.state.buffers.depth.getReversed(),zt=H.isInstancedMesh===!0,Zt=H.isBatchedMesh===!0,Ce=!!y.map,ue=!!y.matcap,De=!!tt,G=!!y.aoMap,on=!!y.lightMap,ae=!!y.bumpMap,ce=!!y.normalMap,Wt=!!y.displacementMap,Ae=!!y.emissiveMap,Ht=!!y.metalnessMap,I=!!y.roughnessMap,b=y.anisotropy>0,q=y.clearcoat>0,ot=y.dispersion>0,lt=y.iridescence>0,rt=y.sheen>0,Ft=y.transmission>0,Mt=b&&!!y.anisotropyMap,Ct=q&&!!y.clearcoatMap,de=q&&!!y.clearcoatNormalMap,dt=q&&!!y.clearcoatRoughnessMap,Pt=lt&&!!y.iridescenceMap,Xt=lt&&!!y.iridescenceThicknessMap,Yt=rt&&!!y.sheenColorMap,Lt=rt&&!!y.sheenRoughnessMap,he=!!y.specularMap,ee=!!y.specularColorMap,ye=!!y.specularIntensityMap,z=Ft&&!!y.transmissionMap,xt=Ft&&!!y.thicknessMap,Z=!!y.gradientMap,at=!!y.alphaMap,Et=y.alphaTest>0,St=!!y.alphaHash,Qt=!!y.extensions;let Re=Ti;y.toneMapped&&(it===null||it.isXRRenderTarget===!0)&&(Re=i.toneMapping);const We={shaderID:ct,shaderType:y.type,shaderName:y.name,vertexShader:wt,fragmentShader:X,defines:y.defines,customVertexShaderID:K,customFragmentShaderID:nt,isRawShaderMaterial:y.isRawShaderMaterial===!0,glslVersion:y.glslVersion,precision:p,batching:Zt,batchingColor:Zt&&H._colorsTexture!==null,instancing:zt,instancingColor:zt&&H.instanceColor!==null,instancingMorph:zt&&H.morphTexture!==null,supportsVertexTextures:f,outputColorSpace:it===null?i.outputColorSpace:it.isXRRenderTarget===!0?it.texture.colorSpace:Us,alphaToCoverage:!!y.alphaToCoverage,map:Ce,matcap:ue,envMap:De,envMapMode:De&&tt.mapping,envMapCubeUVHeight:W,aoMap:G,lightMap:on,bumpMap:ae,normalMap:ce,displacementMap:f&&Wt,emissiveMap:Ae,normalMapObjectSpace:ce&&y.normalMapType===Zd,normalMapTangentSpace:ce&&y.normalMapType===Oo,metalnessMap:Ht,roughnessMap:I,anisotropy:b,anisotropyMap:Mt,clearcoat:q,clearcoatMap:Ct,clearcoatNormalMap:de,clearcoatRoughnessMap:dt,dispersion:ot,iridescence:lt,iridescenceMap:Pt,iridescenceThicknessMap:Xt,sheen:rt,sheenColorMap:Yt,sheenRoughnessMap:Lt,specularMap:he,specularColorMap:ee,specularIntensityMap:ye,transmission:Ft,transmissionMap:z,thicknessMap:xt,gradientMap:Z,opaque:y.transparent===!1&&y.blending===vs&&y.alphaToCoverage===!1,alphaMap:at,alphaTest:Et,alphaHash:St,combine:y.combine,mapUv:Ce&&_(y.map.channel),aoMapUv:G&&_(y.aoMap.channel),lightMapUv:on&&_(y.lightMap.channel),bumpMapUv:ae&&_(y.bumpMap.channel),normalMapUv:ce&&_(y.normalMap.channel),displacementMapUv:Wt&&_(y.displacementMap.channel),emissiveMapUv:Ae&&_(y.emissiveMap.channel),metalnessMapUv:Ht&&_(y.metalnessMap.channel),roughnessMapUv:I&&_(y.roughnessMap.channel),anisotropyMapUv:Mt&&_(y.anisotropyMap.channel),clearcoatMapUv:Ct&&_(y.clearcoatMap.channel),clearcoatNormalMapUv:de&&_(y.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:dt&&_(y.clearcoatRoughnessMap.channel),iridescenceMapUv:Pt&&_(y.iridescenceMap.channel),iridescenceThicknessMapUv:Xt&&_(y.iridescenceThicknessMap.channel),sheenColorMapUv:Yt&&_(y.sheenColorMap.channel),sheenRoughnessMapUv:Lt&&_(y.sheenRoughnessMap.channel),specularMapUv:he&&_(y.specularMap.channel),specularColorMapUv:ee&&_(y.specularColorMap.channel),specularIntensityMapUv:ye&&_(y.specularIntensityMap.channel),transmissionMapUv:z&&_(y.transmissionMap.channel),thicknessMapUv:xt&&_(y.thicknessMap.channel),alphaMapUv:at&&_(y.alphaMap.channel),vertexTangents:!!Q.attributes.tangent&&(ce||b),vertexColors:y.vertexColors,vertexAlphas:y.vertexColors===!0&&!!Q.attributes.color&&Q.attributes.color.itemSize===4,pointsUvs:H.isPoints===!0&&!!Q.attributes.uv&&(Ce||at),fog:!!J,useFog:y.fog===!0,fogExp2:!!J&&J.isFogExp2,flatShading:y.flatShading===!0,sizeAttenuation:y.sizeAttenuation===!0,logarithmicDepthBuffer:u,reverseDepthBuffer:vt,skinning:H.isSkinnedMesh===!0,morphTargets:Q.morphAttributes.position!==void 0,morphNormals:Q.morphAttributes.normal!==void 0,morphColors:Q.morphAttributes.color!==void 0,morphTargetsCount:pt,morphTextureStride:Rt,numDirLights:S.directional.length,numPointLights:S.point.length,numSpotLights:S.spot.length,numSpotLightMaps:S.spotLightMap.length,numRectAreaLights:S.rectArea.length,numHemiLights:S.hemi.length,numDirLightShadows:S.directionalShadowMap.length,numPointLightShadows:S.pointShadowMap.length,numSpotLightShadows:S.spotShadowMap.length,numSpotLightShadowsWithMaps:S.numSpotLightShadowsWithMaps,numLightProbes:S.numLightProbes,numClippingPlanes:a.numPlanes,numClipIntersection:a.numIntersection,dithering:y.dithering,shadowMapEnabled:i.shadowMap.enabled&&U.length>0,shadowMapType:i.shadowMap.type,toneMapping:Re,decodeVideoTexture:Ce&&y.map.isVideoTexture===!0&&le.getTransfer(y.map.colorSpace)===Ee,decodeVideoTextureEmissive:Ae&&y.emissiveMap.isVideoTexture===!0&&le.getTransfer(y.emissiveMap.colorSpace)===Ee,premultipliedAlpha:y.premultipliedAlpha,doubleSided:y.side===un,flipSided:y.side===dn,useDepthPacking:y.depthPacking>=0,depthPacking:y.depthPacking||0,index0AttributeName:y.index0AttributeName,extensionClipCullDistance:Qt&&y.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(Qt&&y.extensions.multiDraw===!0||Zt)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:y.customProgramCacheKey()};return We.vertexUv1s=l.has(1),We.vertexUv2s=l.has(2),We.vertexUv3s=l.has(3),l.clear(),We}function d(y){const S=[];if(y.shaderID?S.push(y.shaderID):(S.push(y.customVertexShaderID),S.push(y.customFragmentShaderID)),y.defines!==void 0)for(const U in y.defines)S.push(U),S.push(y.defines[U]);return y.isRawShaderMaterial===!1&&(w(S,y),T(S,y),S.push(i.outputColorSpace)),S.push(y.customProgramCacheKey),S.join()}function w(y,S){y.push(S.precision),y.push(S.outputColorSpace),y.push(S.envMapMode),y.push(S.envMapCubeUVHeight),y.push(S.mapUv),y.push(S.alphaMapUv),y.push(S.lightMapUv),y.push(S.aoMapUv),y.push(S.bumpMapUv),y.push(S.normalMapUv),y.push(S.displacementMapUv),y.push(S.emissiveMapUv),y.push(S.metalnessMapUv),y.push(S.roughnessMapUv),y.push(S.anisotropyMapUv),y.push(S.clearcoatMapUv),y.push(S.clearcoatNormalMapUv),y.push(S.clearcoatRoughnessMapUv),y.push(S.iridescenceMapUv),y.push(S.iridescenceThicknessMapUv),y.push(S.sheenColorMapUv),y.push(S.sheenRoughnessMapUv),y.push(S.specularMapUv),y.push(S.specularColorMapUv),y.push(S.specularIntensityMapUv),y.push(S.transmissionMapUv),y.push(S.thicknessMapUv),y.push(S.combine),y.push(S.fogExp2),y.push(S.sizeAttenuation),y.push(S.morphTargetsCount),y.push(S.morphAttributeCount),y.push(S.numDirLights),y.push(S.numPointLights),y.push(S.numSpotLights),y.push(S.numSpotLightMaps),y.push(S.numHemiLights),y.push(S.numRectAreaLights),y.push(S.numDirLightShadows),y.push(S.numPointLightShadows),y.push(S.numSpotLightShadows),y.push(S.numSpotLightShadowsWithMaps),y.push(S.numLightProbes),y.push(S.shadowMapType),y.push(S.toneMapping),y.push(S.numClippingPlanes),y.push(S.numClipIntersection),y.push(S.depthPacking)}function T(y,S){o.disableAll(),S.supportsVertexTextures&&o.enable(0),S.instancing&&o.enable(1),S.instancingColor&&o.enable(2),S.instancingMorph&&o.enable(3),S.matcap&&o.enable(4),S.envMap&&o.enable(5),S.normalMapObjectSpace&&o.enable(6),S.normalMapTangentSpace&&o.enable(7),S.clearcoat&&o.enable(8),S.iridescence&&o.enable(9),S.alphaTest&&o.enable(10),S.vertexColors&&o.enable(11),S.vertexAlphas&&o.enable(12),S.vertexUv1s&&o.enable(13),S.vertexUv2s&&o.enable(14),S.vertexUv3s&&o.enable(15),S.vertexTangents&&o.enable(16),S.anisotropy&&o.enable(17),S.alphaHash&&o.enable(18),S.batching&&o.enable(19),S.dispersion&&o.enable(20),S.batchingColor&&o.enable(21),y.push(o.mask),o.disableAll(),S.fog&&o.enable(0),S.useFog&&o.enable(1),S.flatShading&&o.enable(2),S.logarithmicDepthBuffer&&o.enable(3),S.reverseDepthBuffer&&o.enable(4),S.skinning&&o.enable(5),S.morphTargets&&o.enable(6),S.morphNormals&&o.enable(7),S.morphColors&&o.enable(8),S.premultipliedAlpha&&o.enable(9),S.shadowMapEnabled&&o.enable(10),S.doubleSided&&o.enable(11),S.flipSided&&o.enable(12),S.useDepthPacking&&o.enable(13),S.dithering&&o.enable(14),S.transmission&&o.enable(15),S.sheen&&o.enable(16),S.opaque&&o.enable(17),S.pointsUvs&&o.enable(18),S.decodeVideoTexture&&o.enable(19),S.decodeVideoTextureEmissive&&o.enable(20),S.alphaToCoverage&&o.enable(21),y.push(o.mask)}function M(y){const S=g[y.type];let U;if(S){const k=Gn[S];U=Gf.clone(k.uniforms)}else U=y.uniforms;return U}function F(y,S){let U;for(let k=0,H=h.length;k<H;k++){const J=h[k];if(J.cacheKey===S){U=J,++U.usedTimes;break}}return U===void 0&&(U=new n0(i,S,y,r),h.push(U)),U}function P(y){if(--y.usedTimes===0){const S=h.indexOf(y);h[S]=h[h.length-1],h.pop(),y.destroy()}}function N(y){c.remove(y)}function D(){c.dispose()}return{getParameters:m,getProgramCacheKey:d,getUniforms:M,acquireProgram:F,releaseProgram:P,releaseShaderCache:N,programs:h,dispose:D}}function a0(){let i=new WeakMap;function t(a){return i.has(a)}function e(a){let o=i.get(a);return o===void 0&&(o={},i.set(a,o)),o}function n(a){i.delete(a)}function s(a,o,c){i.get(a)[o]=c}function r(){i=new WeakMap}return{has:t,get:e,remove:n,update:s,dispose:r}}function c0(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.material.id!==t.material.id?i.material.id-t.material.id:i.z!==t.z?i.z-t.z:i.id-t.id}function oh(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.z!==t.z?t.z-i.z:i.id-t.id}function ah(){const i=[];let t=0;const e=[],n=[],s=[];function r(){t=0,e.length=0,n.length=0,s.length=0}function a(u,f,p,g,_,m){let d=i[t];return d===void 0?(d={id:u.id,object:u,geometry:f,material:p,groupOrder:g,renderOrder:u.renderOrder,z:_,group:m},i[t]=d):(d.id=u.id,d.object=u,d.geometry=f,d.material=p,d.groupOrder=g,d.renderOrder=u.renderOrder,d.z=_,d.group=m),t++,d}function o(u,f,p,g,_,m){const d=a(u,f,p,g,_,m);p.transmission>0?n.push(d):p.transparent===!0?s.push(d):e.push(d)}function c(u,f,p,g,_,m){const d=a(u,f,p,g,_,m);p.transmission>0?n.unshift(d):p.transparent===!0?s.unshift(d):e.unshift(d)}function l(u,f){e.length>1&&e.sort(u||c0),n.length>1&&n.sort(f||oh),s.length>1&&s.sort(f||oh)}function h(){for(let u=t,f=i.length;u<f;u++){const p=i[u];if(p.id===null)break;p.id=null,p.object=null,p.geometry=null,p.material=null,p.group=null}}return{opaque:e,transmissive:n,transparent:s,init:r,push:o,unshift:c,finish:h,sort:l}}function l0(){let i=new WeakMap;function t(n,s){const r=i.get(n);let a;return r===void 0?(a=new ah,i.set(n,[a])):s>=r.length?(a=new ah,r.push(a)):a=r[s],a}function e(){i=new WeakMap}return{get:t,dispose:e}}function h0(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={direction:new L,color:new Kt};break;case"SpotLight":e={position:new L,direction:new L,color:new Kt,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":e={position:new L,color:new Kt,distance:0,decay:0};break;case"HemisphereLight":e={direction:new L,skyColor:new Kt,groundColor:new Kt};break;case"RectAreaLight":e={color:new Kt,position:new L,halfWidth:new L,halfHeight:new L};break}return i[t.id]=e,e}}}function u0(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At};break;case"SpotLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At};break;case"PointLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At,shadowCameraNear:1,shadowCameraFar:1e3};break}return i[t.id]=e,e}}}let d0=0;function f0(i,t){return(t.castShadow?2:0)-(i.castShadow?2:0)+(t.map?1:0)-(i.map?1:0)}function p0(i){const t=new h0,e=u0(),n={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let l=0;l<9;l++)n.probe.push(new L);const s=new L,r=new jt,a=new jt;function o(l){let h=0,u=0,f=0;for(let y=0;y<9;y++)n.probe[y].set(0,0,0);let p=0,g=0,_=0,m=0,d=0,w=0,T=0,M=0,F=0,P=0,N=0;l.sort(f0);for(let y=0,S=l.length;y<S;y++){const U=l[y],k=U.color,H=U.intensity,J=U.distance,Q=U.shadow&&U.shadow.map?U.shadow.map.texture:null;if(U.isAmbientLight)h+=k.r*H,u+=k.g*H,f+=k.b*H;else if(U.isLightProbe){for(let O=0;O<9;O++)n.probe[O].addScaledVector(U.sh.coefficients[O],H);N++}else if(U.isDirectionalLight){const O=t.get(U);if(O.color.copy(U.color).multiplyScalar(U.intensity),U.castShadow){const tt=U.shadow,W=e.get(U);W.shadowIntensity=tt.intensity,W.shadowBias=tt.bias,W.shadowNormalBias=tt.normalBias,W.shadowRadius=tt.radius,W.shadowMapSize=tt.mapSize,n.directionalShadow[p]=W,n.directionalShadowMap[p]=Q,n.directionalShadowMatrix[p]=U.shadow.matrix,w++}n.directional[p]=O,p++}else if(U.isSpotLight){const O=t.get(U);O.position.setFromMatrixPosition(U.matrixWorld),O.color.copy(k).multiplyScalar(H),O.distance=J,O.coneCos=Math.cos(U.angle),O.penumbraCos=Math.cos(U.angle*(1-U.penumbra)),O.decay=U.decay,n.spot[_]=O;const tt=U.shadow;if(U.map&&(n.spotLightMap[F]=U.map,F++,tt.updateMatrices(U),U.castShadow&&P++),n.spotLightMatrix[_]=tt.matrix,U.castShadow){const W=e.get(U);W.shadowIntensity=tt.intensity,W.shadowBias=tt.bias,W.shadowNormalBias=tt.normalBias,W.shadowRadius=tt.radius,W.shadowMapSize=tt.mapSize,n.spotShadow[_]=W,n.spotShadowMap[_]=Q,M++}_++}else if(U.isRectAreaLight){const O=t.get(U);O.color.copy(k).multiplyScalar(H),O.halfWidth.set(U.width*.5,0,0),O.halfHeight.set(0,U.height*.5,0),n.rectArea[m]=O,m++}else if(U.isPointLight){const O=t.get(U);if(O.color.copy(U.color).multiplyScalar(U.intensity),O.distance=U.distance,O.decay=U.decay,U.castShadow){const tt=U.shadow,W=e.get(U);W.shadowIntensity=tt.intensity,W.shadowBias=tt.bias,W.shadowNormalBias=tt.normalBias,W.shadowRadius=tt.radius,W.shadowMapSize=tt.mapSize,W.shadowCameraNear=tt.camera.near,W.shadowCameraFar=tt.camera.far,n.pointShadow[g]=W,n.pointShadowMap[g]=Q,n.pointShadowMatrix[g]=U.shadow.matrix,T++}n.point[g]=O,g++}else if(U.isHemisphereLight){const O=t.get(U);O.skyColor.copy(U.color).multiplyScalar(H),O.groundColor.copy(U.groundColor).multiplyScalar(H),n.hemi[d]=O,d++}}m>0&&(i.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=_t.LTC_FLOAT_1,n.rectAreaLTC2=_t.LTC_FLOAT_2):(n.rectAreaLTC1=_t.LTC_HALF_1,n.rectAreaLTC2=_t.LTC_HALF_2)),n.ambient[0]=h,n.ambient[1]=u,n.ambient[2]=f;const D=n.hash;(D.directionalLength!==p||D.pointLength!==g||D.spotLength!==_||D.rectAreaLength!==m||D.hemiLength!==d||D.numDirectionalShadows!==w||D.numPointShadows!==T||D.numSpotShadows!==M||D.numSpotMaps!==F||D.numLightProbes!==N)&&(n.directional.length=p,n.spot.length=_,n.rectArea.length=m,n.point.length=g,n.hemi.length=d,n.directionalShadow.length=w,n.directionalShadowMap.length=w,n.pointShadow.length=T,n.pointShadowMap.length=T,n.spotShadow.length=M,n.spotShadowMap.length=M,n.directionalShadowMatrix.length=w,n.pointShadowMatrix.length=T,n.spotLightMatrix.length=M+F-P,n.spotLightMap.length=F,n.numSpotLightShadowsWithMaps=P,n.numLightProbes=N,D.directionalLength=p,D.pointLength=g,D.spotLength=_,D.rectAreaLength=m,D.hemiLength=d,D.numDirectionalShadows=w,D.numPointShadows=T,D.numSpotShadows=M,D.numSpotMaps=F,D.numLightProbes=N,n.version=d0++)}function c(l,h){let u=0,f=0,p=0,g=0,_=0;const m=h.matrixWorldInverse;for(let d=0,w=l.length;d<w;d++){const T=l[d];if(T.isDirectionalLight){const M=n.directional[u];M.direction.setFromMatrixPosition(T.matrixWorld),s.setFromMatrixPosition(T.target.matrixWorld),M.direction.sub(s),M.direction.transformDirection(m),u++}else if(T.isSpotLight){const M=n.spot[p];M.position.setFromMatrixPosition(T.matrixWorld),M.position.applyMatrix4(m),M.direction.setFromMatrixPosition(T.matrixWorld),s.setFromMatrixPosition(T.target.matrixWorld),M.direction.sub(s),M.direction.transformDirection(m),p++}else if(T.isRectAreaLight){const M=n.rectArea[g];M.position.setFromMatrixPosition(T.matrixWorld),M.position.applyMatrix4(m),a.identity(),r.copy(T.matrixWorld),r.premultiply(m),a.extractRotation(r),M.halfWidth.set(T.width*.5,0,0),M.halfHeight.set(0,T.height*.5,0),M.halfWidth.applyMatrix4(a),M.halfHeight.applyMatrix4(a),g++}else if(T.isPointLight){const M=n.point[f];M.position.setFromMatrixPosition(T.matrixWorld),M.position.applyMatrix4(m),f++}else if(T.isHemisphereLight){const M=n.hemi[_];M.direction.setFromMatrixPosition(T.matrixWorld),M.direction.transformDirection(m),_++}}}return{setup:o,setupView:c,state:n}}function ch(i){const t=new p0(i),e=[],n=[];function s(h){l.camera=h,e.length=0,n.length=0}function r(h){e.push(h)}function a(h){n.push(h)}function o(){t.setup(e)}function c(h){t.setupView(e,h)}const l={lightsArray:e,shadowsArray:n,camera:null,lights:t,transmissionRenderTarget:{}};return{init:s,state:l,setupLights:o,setupLightsView:c,pushLight:r,pushShadow:a}}function m0(i){let t=new WeakMap;function e(s,r=0){const a=t.get(s);let o;return a===void 0?(o=new ch(i),t.set(s,[o])):r>=a.length?(o=new ch(i),a.push(o)):o=a[r],o}function n(){t=new WeakMap}return{get:e,dispose:n}}class g0 extends Hn{static get type(){return"MeshDepthMaterial"}constructor(t){super(),this.isMeshDepthMaterial=!0,this.depthPacking=Kd,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(t)}copy(t){return super.copy(t),this.depthPacking=t.depthPacking,this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this}}class _0 extends Hn{static get type(){return"MeshDistanceMaterial"}constructor(t){super(),this.isMeshDistanceMaterial=!0,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(t)}copy(t){return super.copy(t),this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this}}const v0=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,x0=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function y0(i,t,e){let n=new Wc;const s=new At,r=new At,a=new xe,o=new g0({depthPacking:Jd}),c=new _0,l={},h=e.maxTextureSize,u={[ai]:dn,[dn]:ai,[un]:un},f=new Ci({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new At},radius:{value:4}},vertexShader:v0,fragmentShader:x0}),p=f.clone();p.defines.HORIZONTAL_PASS=1;const g=new Pe;g.setAttribute("position",new xn(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const _=new me(g,f),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=$h;let d=this.type;this.render=function(P,N,D){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||P.length===0)return;const y=i.getRenderTarget(),S=i.getActiveCubeFace(),U=i.getActiveMipmapLevel(),k=i.state;k.setBlending(wi),k.buffers.color.setClear(1,1,1,1),k.buffers.depth.setTest(!0),k.setScissorTest(!1);const H=d!==ni&&this.type===ni,J=d===ni&&this.type!==ni;for(let Q=0,O=P.length;Q<O;Q++){const tt=P[Q],W=tt.shadow;if(W===void 0){console.warn("THREE.WebGLShadowMap:",tt,"has no shadow.");continue}if(W.autoUpdate===!1&&W.needsUpdate===!1)continue;s.copy(W.mapSize);const ct=W.getFrameExtents();if(s.multiply(ct),r.copy(W.mapSize),(s.x>h||s.y>h)&&(s.x>h&&(r.x=Math.floor(h/ct.x),s.x=r.x*ct.x,W.mapSize.x=r.x),s.y>h&&(r.y=Math.floor(h/ct.y),s.y=r.y*ct.y,W.mapSize.y=r.y)),W.map===null||H===!0||J===!0){const pt=this.type!==ni?{minFilter:vn,magFilter:vn}:{};W.map!==null&&W.map.dispose(),W.map=new qi(s.x,s.y,pt),W.map.texture.name=tt.name+".shadowMap",W.camera.updateProjectionMatrix()}i.setRenderTarget(W.map),i.clear();const ft=W.getViewportCount();for(let pt=0;pt<ft;pt++){const Rt=W.getViewport(pt);a.set(r.x*Rt.x,r.y*Rt.y,r.x*Rt.z,r.y*Rt.w),k.viewport(a),W.updateMatrices(tt,pt),n=W.getFrustum(),M(N,D,W.camera,tt,this.type)}W.isPointLightShadow!==!0&&this.type===ni&&w(W,D),W.needsUpdate=!1}d=this.type,m.needsUpdate=!1,i.setRenderTarget(y,S,U)};function w(P,N){const D=t.update(_);f.defines.VSM_SAMPLES!==P.blurSamples&&(f.defines.VSM_SAMPLES=P.blurSamples,p.defines.VSM_SAMPLES=P.blurSamples,f.needsUpdate=!0,p.needsUpdate=!0),P.mapPass===null&&(P.mapPass=new qi(s.x,s.y)),f.uniforms.shadow_pass.value=P.map.texture,f.uniforms.resolution.value=P.mapSize,f.uniforms.radius.value=P.radius,i.setRenderTarget(P.mapPass),i.clear(),i.renderBufferDirect(N,null,D,f,_,null),p.uniforms.shadow_pass.value=P.mapPass.texture,p.uniforms.resolution.value=P.mapSize,p.uniforms.radius.value=P.radius,i.setRenderTarget(P.map),i.clear(),i.renderBufferDirect(N,null,D,p,_,null)}function T(P,N,D,y){let S=null;const U=D.isPointLight===!0?P.customDistanceMaterial:P.customDepthMaterial;if(U!==void 0)S=U;else if(S=D.isPointLight===!0?c:o,i.localClippingEnabled&&N.clipShadows===!0&&Array.isArray(N.clippingPlanes)&&N.clippingPlanes.length!==0||N.displacementMap&&N.displacementScale!==0||N.alphaMap&&N.alphaTest>0||N.map&&N.alphaTest>0){const k=S.uuid,H=N.uuid;let J=l[k];J===void 0&&(J={},l[k]=J);let Q=J[H];Q===void 0&&(Q=S.clone(),J[H]=Q,N.addEventListener("dispose",F)),S=Q}if(S.visible=N.visible,S.wireframe=N.wireframe,y===ni?S.side=N.shadowSide!==null?N.shadowSide:N.side:S.side=N.shadowSide!==null?N.shadowSide:u[N.side],S.alphaMap=N.alphaMap,S.alphaTest=N.alphaTest,S.map=N.map,S.clipShadows=N.clipShadows,S.clippingPlanes=N.clippingPlanes,S.clipIntersection=N.clipIntersection,S.displacementMap=N.displacementMap,S.displacementScale=N.displacementScale,S.displacementBias=N.displacementBias,S.wireframeLinewidth=N.wireframeLinewidth,S.linewidth=N.linewidth,D.isPointLight===!0&&S.isMeshDistanceMaterial===!0){const k=i.properties.get(S);k.light=D}return S}function M(P,N,D,y,S){if(P.visible===!1)return;if(P.layers.test(N.layers)&&(P.isMesh||P.isLine||P.isPoints)&&(P.castShadow||P.receiveShadow&&S===ni)&&(!P.frustumCulled||n.intersectsObject(P))){P.modelViewMatrix.multiplyMatrices(D.matrixWorldInverse,P.matrixWorld);const H=t.update(P),J=P.material;if(Array.isArray(J)){const Q=H.groups;for(let O=0,tt=Q.length;O<tt;O++){const W=Q[O],ct=J[W.materialIndex];if(ct&&ct.visible){const ft=T(P,ct,y,S);P.onBeforeShadow(i,P,N,D,H,ft,W),i.renderBufferDirect(D,null,H,ft,P,W),P.onAfterShadow(i,P,N,D,H,ft,W)}}}else if(J.visible){const Q=T(P,J,y,S);P.onBeforeShadow(i,P,N,D,H,Q,null),i.renderBufferDirect(D,null,H,Q,P,null),P.onAfterShadow(i,P,N,D,H,Q,null)}}const k=P.children;for(let H=0,J=k.length;H<J;H++)M(k[H],N,D,y,S)}function F(P){P.target.removeEventListener("dispose",F);for(const D in l){const y=l[D],S=P.target.uuid;S in y&&(y[S].dispose(),delete y[S])}}}const M0={[Ga]:Wa,[Xa]:Ya,[qa]:$a,[ws]:ja,[Wa]:Ga,[Ya]:Xa,[$a]:qa,[ja]:ws};function S0(i,t){function e(){let z=!1;const xt=new xe;let Z=null;const at=new xe(0,0,0,0);return{setMask:function(Et){Z!==Et&&!z&&(i.colorMask(Et,Et,Et,Et),Z=Et)},setLocked:function(Et){z=Et},setClear:function(Et,St,Qt,Re,We){We===!0&&(Et*=Re,St*=Re,Qt*=Re),xt.set(Et,St,Qt,Re),at.equals(xt)===!1&&(i.clearColor(Et,St,Qt,Re),at.copy(xt))},reset:function(){z=!1,Z=null,at.set(-1,0,0,0)}}}function n(){let z=!1,xt=!1,Z=null,at=null,Et=null;return{setReversed:function(St){if(xt!==St){const Qt=t.get("EXT_clip_control");xt?Qt.clipControlEXT(Qt.LOWER_LEFT_EXT,Qt.ZERO_TO_ONE_EXT):Qt.clipControlEXT(Qt.LOWER_LEFT_EXT,Qt.NEGATIVE_ONE_TO_ONE_EXT);const Re=Et;Et=null,this.setClear(Re)}xt=St},getReversed:function(){return xt},setTest:function(St){St?it(i.DEPTH_TEST):vt(i.DEPTH_TEST)},setMask:function(St){Z!==St&&!z&&(i.depthMask(St),Z=St)},setFunc:function(St){if(xt&&(St=M0[St]),at!==St){switch(St){case Ga:i.depthFunc(i.NEVER);break;case Wa:i.depthFunc(i.ALWAYS);break;case Xa:i.depthFunc(i.LESS);break;case ws:i.depthFunc(i.LEQUAL);break;case qa:i.depthFunc(i.EQUAL);break;case ja:i.depthFunc(i.GEQUAL);break;case Ya:i.depthFunc(i.GREATER);break;case $a:i.depthFunc(i.NOTEQUAL);break;default:i.depthFunc(i.LEQUAL)}at=St}},setLocked:function(St){z=St},setClear:function(St){Et!==St&&(xt&&(St=1-St),i.clearDepth(St),Et=St)},reset:function(){z=!1,Z=null,at=null,Et=null,xt=!1}}}function s(){let z=!1,xt=null,Z=null,at=null,Et=null,St=null,Qt=null,Re=null,We=null;return{setTest:function(ie){z||(ie?it(i.STENCIL_TEST):vt(i.STENCIL_TEST))},setMask:function(ie){xt!==ie&&!z&&(i.stencilMask(ie),xt=ie)},setFunc:function(ie,an,Pn){(Z!==ie||at!==an||Et!==Pn)&&(i.stencilFunc(ie,an,Pn),Z=ie,at=an,Et=Pn)},setOp:function(ie,an,Pn){(St!==ie||Qt!==an||Re!==Pn)&&(i.stencilOp(ie,an,Pn),St=ie,Qt=an,Re=Pn)},setLocked:function(ie){z=ie},setClear:function(ie){We!==ie&&(i.clearStencil(ie),We=ie)},reset:function(){z=!1,xt=null,Z=null,at=null,Et=null,St=null,Qt=null,Re=null,We=null}}}const r=new e,a=new n,o=new s,c=new WeakMap,l=new WeakMap;let h={},u={},f=new WeakMap,p=[],g=null,_=!1,m=null,d=null,w=null,T=null,M=null,F=null,P=null,N=new Kt(0,0,0),D=0,y=!1,S=null,U=null,k=null,H=null,J=null;const Q=i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let O=!1,tt=0;const W=i.getParameter(i.VERSION);W.indexOf("WebGL")!==-1?(tt=parseFloat(/^WebGL (\d)/.exec(W)[1]),O=tt>=1):W.indexOf("OpenGL ES")!==-1&&(tt=parseFloat(/^OpenGL ES (\d)/.exec(W)[1]),O=tt>=2);let ct=null,ft={};const pt=i.getParameter(i.SCISSOR_BOX),Rt=i.getParameter(i.VIEWPORT),wt=new xe().fromArray(pt),X=new xe().fromArray(Rt);function K(z,xt,Z,at){const Et=new Uint8Array(4),St=i.createTexture();i.bindTexture(z,St),i.texParameteri(z,i.TEXTURE_MIN_FILTER,i.NEAREST),i.texParameteri(z,i.TEXTURE_MAG_FILTER,i.NEAREST);for(let Qt=0;Qt<Z;Qt++)z===i.TEXTURE_3D||z===i.TEXTURE_2D_ARRAY?i.texImage3D(xt,0,i.RGBA,1,1,at,0,i.RGBA,i.UNSIGNED_BYTE,Et):i.texImage2D(xt+Qt,0,i.RGBA,1,1,0,i.RGBA,i.UNSIGNED_BYTE,Et);return St}const nt={};nt[i.TEXTURE_2D]=K(i.TEXTURE_2D,i.TEXTURE_2D,1),nt[i.TEXTURE_CUBE_MAP]=K(i.TEXTURE_CUBE_MAP,i.TEXTURE_CUBE_MAP_POSITIVE_X,6),nt[i.TEXTURE_2D_ARRAY]=K(i.TEXTURE_2D_ARRAY,i.TEXTURE_2D_ARRAY,1,1),nt[i.TEXTURE_3D]=K(i.TEXTURE_3D,i.TEXTURE_3D,1,1),r.setClear(0,0,0,1),a.setClear(1),o.setClear(0),it(i.DEPTH_TEST),a.setFunc(ws),ae(!1),ce(al),it(i.CULL_FACE),G(wi);function it(z){h[z]!==!0&&(i.enable(z),h[z]=!0)}function vt(z){h[z]!==!1&&(i.disable(z),h[z]=!1)}function zt(z,xt){return u[z]!==xt?(i.bindFramebuffer(z,xt),u[z]=xt,z===i.DRAW_FRAMEBUFFER&&(u[i.FRAMEBUFFER]=xt),z===i.FRAMEBUFFER&&(u[i.DRAW_FRAMEBUFFER]=xt),!0):!1}function Zt(z,xt){let Z=p,at=!1;if(z){Z=f.get(xt),Z===void 0&&(Z=[],f.set(xt,Z));const Et=z.textures;if(Z.length!==Et.length||Z[0]!==i.COLOR_ATTACHMENT0){for(let St=0,Qt=Et.length;St<Qt;St++)Z[St]=i.COLOR_ATTACHMENT0+St;Z.length=Et.length,at=!0}}else Z[0]!==i.BACK&&(Z[0]=i.BACK,at=!0);at&&i.drawBuffers(Z)}function Ce(z){return g!==z?(i.useProgram(z),g=z,!0):!1}const ue={[Hi]:i.FUNC_ADD,[Sd]:i.FUNC_SUBTRACT,[bd]:i.FUNC_REVERSE_SUBTRACT};ue[Ed]=i.MIN,ue[wd]=i.MAX;const De={[Td]:i.ZERO,[Ad]:i.ONE,[Cd]:i.SRC_COLOR,[Va]:i.SRC_ALPHA,[Id]:i.SRC_ALPHA_SATURATE,[Nd]:i.DST_COLOR,[Pd]:i.DST_ALPHA,[Rd]:i.ONE_MINUS_SRC_COLOR,[Ha]:i.ONE_MINUS_SRC_ALPHA,[Dd]:i.ONE_MINUS_DST_COLOR,[Ld]:i.ONE_MINUS_DST_ALPHA,[Ud]:i.CONSTANT_COLOR,[Fd]:i.ONE_MINUS_CONSTANT_COLOR,[Od]:i.CONSTANT_ALPHA,[kd]:i.ONE_MINUS_CONSTANT_ALPHA};function G(z,xt,Z,at,Et,St,Qt,Re,We,ie){if(z===wi){_===!0&&(vt(i.BLEND),_=!1);return}if(_===!1&&(it(i.BLEND),_=!0),z!==Md){if(z!==m||ie!==y){if((d!==Hi||M!==Hi)&&(i.blendEquation(i.FUNC_ADD),d=Hi,M=Hi),ie)switch(z){case vs:i.blendFuncSeparate(i.ONE,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case cl:i.blendFunc(i.ONE,i.ONE);break;case ll:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case hl:i.blendFuncSeparate(i.ZERO,i.SRC_COLOR,i.ZERO,i.SRC_ALPHA);break;default:console.error("THREE.WebGLState: Invalid blending: ",z);break}else switch(z){case vs:i.blendFuncSeparate(i.SRC_ALPHA,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case cl:i.blendFunc(i.SRC_ALPHA,i.ONE);break;case ll:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case hl:i.blendFunc(i.ZERO,i.SRC_COLOR);break;default:console.error("THREE.WebGLState: Invalid blending: ",z);break}w=null,T=null,F=null,P=null,N.set(0,0,0),D=0,m=z,y=ie}return}Et=Et||xt,St=St||Z,Qt=Qt||at,(xt!==d||Et!==M)&&(i.blendEquationSeparate(ue[xt],ue[Et]),d=xt,M=Et),(Z!==w||at!==T||St!==F||Qt!==P)&&(i.blendFuncSeparate(De[Z],De[at],De[St],De[Qt]),w=Z,T=at,F=St,P=Qt),(Re.equals(N)===!1||We!==D)&&(i.blendColor(Re.r,Re.g,Re.b,We),N.copy(Re),D=We),m=z,y=!1}function on(z,xt){z.side===un?vt(i.CULL_FACE):it(i.CULL_FACE);let Z=z.side===dn;xt&&(Z=!Z),ae(Z),z.blending===vs&&z.transparent===!1?G(wi):G(z.blending,z.blendEquation,z.blendSrc,z.blendDst,z.blendEquationAlpha,z.blendSrcAlpha,z.blendDstAlpha,z.blendColor,z.blendAlpha,z.premultipliedAlpha),a.setFunc(z.depthFunc),a.setTest(z.depthTest),a.setMask(z.depthWrite),r.setMask(z.colorWrite);const at=z.stencilWrite;o.setTest(at),at&&(o.setMask(z.stencilWriteMask),o.setFunc(z.stencilFunc,z.stencilRef,z.stencilFuncMask),o.setOp(z.stencilFail,z.stencilZFail,z.stencilZPass)),Ae(z.polygonOffset,z.polygonOffsetFactor,z.polygonOffsetUnits),z.alphaToCoverage===!0?it(i.SAMPLE_ALPHA_TO_COVERAGE):vt(i.SAMPLE_ALPHA_TO_COVERAGE)}function ae(z){S!==z&&(z?i.frontFace(i.CW):i.frontFace(i.CCW),S=z)}function ce(z){z!==vd?(it(i.CULL_FACE),z!==U&&(z===al?i.cullFace(i.BACK):z===xd?i.cullFace(i.FRONT):i.cullFace(i.FRONT_AND_BACK))):vt(i.CULL_FACE),U=z}function Wt(z){z!==k&&(O&&i.lineWidth(z),k=z)}function Ae(z,xt,Z){z?(it(i.POLYGON_OFFSET_FILL),(H!==xt||J!==Z)&&(i.polygonOffset(xt,Z),H=xt,J=Z)):vt(i.POLYGON_OFFSET_FILL)}function Ht(z){z?it(i.SCISSOR_TEST):vt(i.SCISSOR_TEST)}function I(z){z===void 0&&(z=i.TEXTURE0+Q-1),ct!==z&&(i.activeTexture(z),ct=z)}function b(z,xt,Z){Z===void 0&&(ct===null?Z=i.TEXTURE0+Q-1:Z=ct);let at=ft[Z];at===void 0&&(at={type:void 0,texture:void 0},ft[Z]=at),(at.type!==z||at.texture!==xt)&&(ct!==Z&&(i.activeTexture(Z),ct=Z),i.bindTexture(z,xt||nt[z]),at.type=z,at.texture=xt)}function q(){const z=ft[ct];z!==void 0&&z.type!==void 0&&(i.bindTexture(z.type,null),z.type=void 0,z.texture=void 0)}function ot(){try{i.compressedTexImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function lt(){try{i.compressedTexImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function rt(){try{i.texSubImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Ft(){try{i.texSubImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Mt(){try{i.compressedTexSubImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Ct(){try{i.compressedTexSubImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function de(){try{i.texStorage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function dt(){try{i.texStorage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Pt(){try{i.texImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Xt(){try{i.texImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Yt(z){wt.equals(z)===!1&&(i.scissor(z.x,z.y,z.z,z.w),wt.copy(z))}function Lt(z){X.equals(z)===!1&&(i.viewport(z.x,z.y,z.z,z.w),X.copy(z))}function he(z,xt){let Z=l.get(xt);Z===void 0&&(Z=new WeakMap,l.set(xt,Z));let at=Z.get(z);at===void 0&&(at=i.getUniformBlockIndex(xt,z.name),Z.set(z,at))}function ee(z,xt){const at=l.get(xt).get(z);c.get(xt)!==at&&(i.uniformBlockBinding(xt,at,z.__bindingPointIndex),c.set(xt,at))}function ye(){i.disable(i.BLEND),i.disable(i.CULL_FACE),i.disable(i.DEPTH_TEST),i.disable(i.POLYGON_OFFSET_FILL),i.disable(i.SCISSOR_TEST),i.disable(i.STENCIL_TEST),i.disable(i.SAMPLE_ALPHA_TO_COVERAGE),i.blendEquation(i.FUNC_ADD),i.blendFunc(i.ONE,i.ZERO),i.blendFuncSeparate(i.ONE,i.ZERO,i.ONE,i.ZERO),i.blendColor(0,0,0,0),i.colorMask(!0,!0,!0,!0),i.clearColor(0,0,0,0),i.depthMask(!0),i.depthFunc(i.LESS),a.setReversed(!1),i.clearDepth(1),i.stencilMask(4294967295),i.stencilFunc(i.ALWAYS,0,4294967295),i.stencilOp(i.KEEP,i.KEEP,i.KEEP),i.clearStencil(0),i.cullFace(i.BACK),i.frontFace(i.CCW),i.polygonOffset(0,0),i.activeTexture(i.TEXTURE0),i.bindFramebuffer(i.FRAMEBUFFER,null),i.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),i.bindFramebuffer(i.READ_FRAMEBUFFER,null),i.useProgram(null),i.lineWidth(1),i.scissor(0,0,i.canvas.width,i.canvas.height),i.viewport(0,0,i.canvas.width,i.canvas.height),h={},ct=null,ft={},u={},f=new WeakMap,p=[],g=null,_=!1,m=null,d=null,w=null,T=null,M=null,F=null,P=null,N=new Kt(0,0,0),D=0,y=!1,S=null,U=null,k=null,H=null,J=null,wt.set(0,0,i.canvas.width,i.canvas.height),X.set(0,0,i.canvas.width,i.canvas.height),r.reset(),a.reset(),o.reset()}return{buffers:{color:r,depth:a,stencil:o},enable:it,disable:vt,bindFramebuffer:zt,drawBuffers:Zt,useProgram:Ce,setBlending:G,setMaterial:on,setFlipSided:ae,setCullFace:ce,setLineWidth:Wt,setPolygonOffset:Ae,setScissorTest:Ht,activeTexture:I,bindTexture:b,unbindTexture:q,compressedTexImage2D:ot,compressedTexImage3D:lt,texImage2D:Pt,texImage3D:Xt,updateUBOMapping:he,uniformBlockBinding:ee,texStorage2D:de,texStorage3D:dt,texSubImage2D:rt,texSubImage3D:Ft,compressedTexSubImage2D:Mt,compressedTexSubImage3D:Ct,scissor:Yt,viewport:Lt,reset:ye}}function lh(i,t,e,n){const s=b0(n);switch(e){case eu:return i*t;case iu:return i*t;case su:return i*t*2;case ru:return i*t/s.components*s.byteLength;case Bc:return i*t/s.components*s.byteLength;case ou:return i*t*2/s.components*s.byteLength;case zc:return i*t*2/s.components*s.byteLength;case nu:return i*t*3/s.components*s.byteLength;case wn:return i*t*4/s.components*s.byteLength;case Vc:return i*t*4/s.components*s.byteLength;case ho:case uo:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*8;case fo:case po:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case tc:case nc:return Math.max(i,16)*Math.max(t,8)/4;case Qa:case ec:return Math.max(i,8)*Math.max(t,8)/2;case ic:case sc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*8;case rc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case oc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case ac:return Math.floor((i+4)/5)*Math.floor((t+3)/4)*16;case cc:return Math.floor((i+4)/5)*Math.floor((t+4)/5)*16;case lc:return Math.floor((i+5)/6)*Math.floor((t+4)/5)*16;case hc:return Math.floor((i+5)/6)*Math.floor((t+5)/6)*16;case uc:return Math.floor((i+7)/8)*Math.floor((t+4)/5)*16;case dc:return Math.floor((i+7)/8)*Math.floor((t+5)/6)*16;case fc:return Math.floor((i+7)/8)*Math.floor((t+7)/8)*16;case pc:return Math.floor((i+9)/10)*Math.floor((t+4)/5)*16;case mc:return Math.floor((i+9)/10)*Math.floor((t+5)/6)*16;case gc:return Math.floor((i+9)/10)*Math.floor((t+7)/8)*16;case _c:return Math.floor((i+9)/10)*Math.floor((t+9)/10)*16;case vc:return Math.floor((i+11)/12)*Math.floor((t+9)/10)*16;case xc:return Math.floor((i+11)/12)*Math.floor((t+11)/12)*16;case mo:case yc:case Mc:return Math.ceil(i/4)*Math.ceil(t/4)*16;case au:case Sc:return Math.ceil(i/4)*Math.ceil(t/4)*8;case bc:case Ec:return Math.ceil(i/4)*Math.ceil(t/4)*16}throw new Error(`Unable to determine texture byte length for ${e} format.`)}function b0(i){switch(i){case ci:case Zh:return{byteLength:1,components:1};case cr:case Qh:case gr:return{byteLength:2,components:1};case Oc:case kc:return{byteLength:2,components:4};case Xi:case Fc:case Wn:return{byteLength:4,components:1};case tu:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${i}.`)}function E0(i,t,e,n,s,r,a){const o=t.has("WEBGL_multisampled_render_to_texture")?t.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),l=new At,h=new WeakMap;let u;const f=new WeakMap;let p=!1;try{p=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(I,b){return p?new OffscreenCanvas(I,b):lr("canvas")}function _(I,b,q){let ot=1;const lt=Ht(I);if((lt.width>q||lt.height>q)&&(ot=q/Math.max(lt.width,lt.height)),ot<1)if(typeof HTMLImageElement<"u"&&I instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&I instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&I instanceof ImageBitmap||typeof VideoFrame<"u"&&I instanceof VideoFrame){const rt=Math.floor(ot*lt.width),Ft=Math.floor(ot*lt.height);u===void 0&&(u=g(rt,Ft));const Mt=b?g(rt,Ft):u;return Mt.width=rt,Mt.height=Ft,Mt.getContext("2d").drawImage(I,0,0,rt,Ft),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+lt.width+"x"+lt.height+") to ("+rt+"x"+Ft+")."),Mt}else return"data"in I&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+lt.width+"x"+lt.height+")."),I;return I}function m(I){return I.generateMipmaps}function d(I){i.generateMipmap(I)}function w(I){return I.isWebGLCubeRenderTarget?i.TEXTURE_CUBE_MAP:I.isWebGL3DRenderTarget?i.TEXTURE_3D:I.isWebGLArrayRenderTarget||I.isCompressedArrayTexture?i.TEXTURE_2D_ARRAY:i.TEXTURE_2D}function T(I,b,q,ot,lt=!1){if(I!==null){if(i[I]!==void 0)return i[I];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+I+"'")}let rt=b;if(b===i.RED&&(q===i.FLOAT&&(rt=i.R32F),q===i.HALF_FLOAT&&(rt=i.R16F),q===i.UNSIGNED_BYTE&&(rt=i.R8)),b===i.RED_INTEGER&&(q===i.UNSIGNED_BYTE&&(rt=i.R8UI),q===i.UNSIGNED_SHORT&&(rt=i.R16UI),q===i.UNSIGNED_INT&&(rt=i.R32UI),q===i.BYTE&&(rt=i.R8I),q===i.SHORT&&(rt=i.R16I),q===i.INT&&(rt=i.R32I)),b===i.RG&&(q===i.FLOAT&&(rt=i.RG32F),q===i.HALF_FLOAT&&(rt=i.RG16F),q===i.UNSIGNED_BYTE&&(rt=i.RG8)),b===i.RG_INTEGER&&(q===i.UNSIGNED_BYTE&&(rt=i.RG8UI),q===i.UNSIGNED_SHORT&&(rt=i.RG16UI),q===i.UNSIGNED_INT&&(rt=i.RG32UI),q===i.BYTE&&(rt=i.RG8I),q===i.SHORT&&(rt=i.RG16I),q===i.INT&&(rt=i.RG32I)),b===i.RGB_INTEGER&&(q===i.UNSIGNED_BYTE&&(rt=i.RGB8UI),q===i.UNSIGNED_SHORT&&(rt=i.RGB16UI),q===i.UNSIGNED_INT&&(rt=i.RGB32UI),q===i.BYTE&&(rt=i.RGB8I),q===i.SHORT&&(rt=i.RGB16I),q===i.INT&&(rt=i.RGB32I)),b===i.RGBA_INTEGER&&(q===i.UNSIGNED_BYTE&&(rt=i.RGBA8UI),q===i.UNSIGNED_SHORT&&(rt=i.RGBA16UI),q===i.UNSIGNED_INT&&(rt=i.RGBA32UI),q===i.BYTE&&(rt=i.RGBA8I),q===i.SHORT&&(rt=i.RGBA16I),q===i.INT&&(rt=i.RGBA32I)),b===i.RGB&&q===i.UNSIGNED_INT_5_9_9_9_REV&&(rt=i.RGB9_E5),b===i.RGBA){const Ft=lt?ko:le.getTransfer(ot);q===i.FLOAT&&(rt=i.RGBA32F),q===i.HALF_FLOAT&&(rt=i.RGBA16F),q===i.UNSIGNED_BYTE&&(rt=Ft===Ee?i.SRGB8_ALPHA8:i.RGBA8),q===i.UNSIGNED_SHORT_4_4_4_4&&(rt=i.RGBA4),q===i.UNSIGNED_SHORT_5_5_5_1&&(rt=i.RGB5_A1)}return(rt===i.R16F||rt===i.R32F||rt===i.RG16F||rt===i.RG32F||rt===i.RGBA16F||rt===i.RGBA32F)&&t.get("EXT_color_buffer_float"),rt}function M(I,b){let q;return I?b===null||b===Xi||b===Cs?q=i.DEPTH24_STENCIL8:b===Wn?q=i.DEPTH32F_STENCIL8:b===cr&&(q=i.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):b===null||b===Xi||b===Cs?q=i.DEPTH_COMPONENT24:b===Wn?q=i.DEPTH_COMPONENT32F:b===cr&&(q=i.DEPTH_COMPONENT16),q}function F(I,b){return m(I)===!0||I.isFramebufferTexture&&I.minFilter!==vn&&I.minFilter!==_n?Math.log2(Math.max(b.width,b.height))+1:I.mipmaps!==void 0&&I.mipmaps.length>0?I.mipmaps.length:I.isCompressedTexture&&Array.isArray(I.image)?b.mipmaps.length:1}function P(I){const b=I.target;b.removeEventListener("dispose",P),D(b),b.isVideoTexture&&h.delete(b)}function N(I){const b=I.target;b.removeEventListener("dispose",N),S(b)}function D(I){const b=n.get(I);if(b.__webglInit===void 0)return;const q=I.source,ot=f.get(q);if(ot){const lt=ot[b.__cacheKey];lt.usedTimes--,lt.usedTimes===0&&y(I),Object.keys(ot).length===0&&f.delete(q)}n.remove(I)}function y(I){const b=n.get(I);i.deleteTexture(b.__webglTexture);const q=I.source,ot=f.get(q);delete ot[b.__cacheKey],a.memory.textures--}function S(I){const b=n.get(I);if(I.depthTexture&&(I.depthTexture.dispose(),n.remove(I.depthTexture)),I.isWebGLCubeRenderTarget)for(let ot=0;ot<6;ot++){if(Array.isArray(b.__webglFramebuffer[ot]))for(let lt=0;lt<b.__webglFramebuffer[ot].length;lt++)i.deleteFramebuffer(b.__webglFramebuffer[ot][lt]);else i.deleteFramebuffer(b.__webglFramebuffer[ot]);b.__webglDepthbuffer&&i.deleteRenderbuffer(b.__webglDepthbuffer[ot])}else{if(Array.isArray(b.__webglFramebuffer))for(let ot=0;ot<b.__webglFramebuffer.length;ot++)i.deleteFramebuffer(b.__webglFramebuffer[ot]);else i.deleteFramebuffer(b.__webglFramebuffer);if(b.__webglDepthbuffer&&i.deleteRenderbuffer(b.__webglDepthbuffer),b.__webglMultisampledFramebuffer&&i.deleteFramebuffer(b.__webglMultisampledFramebuffer),b.__webglColorRenderbuffer)for(let ot=0;ot<b.__webglColorRenderbuffer.length;ot++)b.__webglColorRenderbuffer[ot]&&i.deleteRenderbuffer(b.__webglColorRenderbuffer[ot]);b.__webglDepthRenderbuffer&&i.deleteRenderbuffer(b.__webglDepthRenderbuffer)}const q=I.textures;for(let ot=0,lt=q.length;ot<lt;ot++){const rt=n.get(q[ot]);rt.__webglTexture&&(i.deleteTexture(rt.__webglTexture),a.memory.textures--),n.remove(q[ot])}n.remove(I)}let U=0;function k(){U=0}function H(){const I=U;return I>=s.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+I+" texture units while this GPU supports only "+s.maxTextures),U+=1,I}function J(I){const b=[];return b.push(I.wrapS),b.push(I.wrapT),b.push(I.wrapR||0),b.push(I.magFilter),b.push(I.minFilter),b.push(I.anisotropy),b.push(I.internalFormat),b.push(I.format),b.push(I.type),b.push(I.generateMipmaps),b.push(I.premultiplyAlpha),b.push(I.flipY),b.push(I.unpackAlignment),b.push(I.colorSpace),b.join()}function Q(I,b){const q=n.get(I);if(I.isVideoTexture&&Wt(I),I.isRenderTargetTexture===!1&&I.version>0&&q.__version!==I.version){const ot=I.image;if(ot===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(ot.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{X(q,I,b);return}}e.bindTexture(i.TEXTURE_2D,q.__webglTexture,i.TEXTURE0+b)}function O(I,b){const q=n.get(I);if(I.version>0&&q.__version!==I.version){X(q,I,b);return}e.bindTexture(i.TEXTURE_2D_ARRAY,q.__webglTexture,i.TEXTURE0+b)}function tt(I,b){const q=n.get(I);if(I.version>0&&q.__version!==I.version){X(q,I,b);return}e.bindTexture(i.TEXTURE_3D,q.__webglTexture,i.TEXTURE0+b)}function W(I,b){const q=n.get(I);if(I.version>0&&q.__version!==I.version){K(q,I,b);return}e.bindTexture(i.TEXTURE_CUBE_MAP,q.__webglTexture,i.TEXTURE0+b)}const ct={[Wi]:i.REPEAT,[On]:i.CLAMP_TO_EDGE,[Za]:i.MIRRORED_REPEAT},ft={[vn]:i.NEAREST,[Yd]:i.NEAREST_MIPMAP_NEAREST,[Rr]:i.NEAREST_MIPMAP_LINEAR,[_n]:i.LINEAR,[Jo]:i.LINEAR_MIPMAP_NEAREST,[si]:i.LINEAR_MIPMAP_LINEAR},pt={[Qd]:i.NEVER,[of]:i.ALWAYS,[tf]:i.LESS,[cu]:i.LEQUAL,[ef]:i.EQUAL,[rf]:i.GEQUAL,[nf]:i.GREATER,[sf]:i.NOTEQUAL};function Rt(I,b){if(b.type===Wn&&t.has("OES_texture_float_linear")===!1&&(b.magFilter===_n||b.magFilter===Jo||b.magFilter===Rr||b.magFilter===si||b.minFilter===_n||b.minFilter===Jo||b.minFilter===Rr||b.minFilter===si)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),i.texParameteri(I,i.TEXTURE_WRAP_S,ct[b.wrapS]),i.texParameteri(I,i.TEXTURE_WRAP_T,ct[b.wrapT]),(I===i.TEXTURE_3D||I===i.TEXTURE_2D_ARRAY)&&i.texParameteri(I,i.TEXTURE_WRAP_R,ct[b.wrapR]),i.texParameteri(I,i.TEXTURE_MAG_FILTER,ft[b.magFilter]),i.texParameteri(I,i.TEXTURE_MIN_FILTER,ft[b.minFilter]),b.compareFunction&&(i.texParameteri(I,i.TEXTURE_COMPARE_MODE,i.COMPARE_REF_TO_TEXTURE),i.texParameteri(I,i.TEXTURE_COMPARE_FUNC,pt[b.compareFunction])),t.has("EXT_texture_filter_anisotropic")===!0){if(b.magFilter===vn||b.minFilter!==Rr&&b.minFilter!==si||b.type===Wn&&t.has("OES_texture_float_linear")===!1)return;if(b.anisotropy>1||n.get(b).__currentAnisotropy){const q=t.get("EXT_texture_filter_anisotropic");i.texParameterf(I,q.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(b.anisotropy,s.getMaxAnisotropy())),n.get(b).__currentAnisotropy=b.anisotropy}}}function wt(I,b){let q=!1;I.__webglInit===void 0&&(I.__webglInit=!0,b.addEventListener("dispose",P));const ot=b.source;let lt=f.get(ot);lt===void 0&&(lt={},f.set(ot,lt));const rt=J(b);if(rt!==I.__cacheKey){lt[rt]===void 0&&(lt[rt]={texture:i.createTexture(),usedTimes:0},a.memory.textures++,q=!0),lt[rt].usedTimes++;const Ft=lt[I.__cacheKey];Ft!==void 0&&(lt[I.__cacheKey].usedTimes--,Ft.usedTimes===0&&y(b)),I.__cacheKey=rt,I.__webglTexture=lt[rt].texture}return q}function X(I,b,q){let ot=i.TEXTURE_2D;(b.isDataArrayTexture||b.isCompressedArrayTexture)&&(ot=i.TEXTURE_2D_ARRAY),b.isData3DTexture&&(ot=i.TEXTURE_3D);const lt=wt(I,b),rt=b.source;e.bindTexture(ot,I.__webglTexture,i.TEXTURE0+q);const Ft=n.get(rt);if(rt.version!==Ft.__version||lt===!0){e.activeTexture(i.TEXTURE0+q);const Mt=le.getPrimaries(le.workingColorSpace),Ct=b.colorSpace===Ei?null:le.getPrimaries(b.colorSpace),de=b.colorSpace===Ei||Mt===Ct?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,b.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,b.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,b.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,de);let dt=_(b.image,!1,s.maxTextureSize);dt=Ae(b,dt);const Pt=r.convert(b.format,b.colorSpace),Xt=r.convert(b.type);let Yt=T(b.internalFormat,Pt,Xt,b.colorSpace,b.isVideoTexture);Rt(ot,b);let Lt;const he=b.mipmaps,ee=b.isVideoTexture!==!0,ye=Ft.__version===void 0||lt===!0,z=rt.dataReady,xt=F(b,dt);if(b.isDepthTexture)Yt=M(b.format===Rs,b.type),ye&&(ee?e.texStorage2D(i.TEXTURE_2D,1,Yt,dt.width,dt.height):e.texImage2D(i.TEXTURE_2D,0,Yt,dt.width,dt.height,0,Pt,Xt,null));else if(b.isDataTexture)if(he.length>0){ee&&ye&&e.texStorage2D(i.TEXTURE_2D,xt,Yt,he[0].width,he[0].height);for(let Z=0,at=he.length;Z<at;Z++)Lt=he[Z],ee?z&&e.texSubImage2D(i.TEXTURE_2D,Z,0,0,Lt.width,Lt.height,Pt,Xt,Lt.data):e.texImage2D(i.TEXTURE_2D,Z,Yt,Lt.width,Lt.height,0,Pt,Xt,Lt.data);b.generateMipmaps=!1}else ee?(ye&&e.texStorage2D(i.TEXTURE_2D,xt,Yt,dt.width,dt.height),z&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,dt.width,dt.height,Pt,Xt,dt.data)):e.texImage2D(i.TEXTURE_2D,0,Yt,dt.width,dt.height,0,Pt,Xt,dt.data);else if(b.isCompressedTexture)if(b.isCompressedArrayTexture){ee&&ye&&e.texStorage3D(i.TEXTURE_2D_ARRAY,xt,Yt,he[0].width,he[0].height,dt.depth);for(let Z=0,at=he.length;Z<at;Z++)if(Lt=he[Z],b.format!==wn)if(Pt!==null)if(ee){if(z)if(b.layerUpdates.size>0){const Et=lh(Lt.width,Lt.height,b.format,b.type);for(const St of b.layerUpdates){const Qt=Lt.data.subarray(St*Et/Lt.data.BYTES_PER_ELEMENT,(St+1)*Et/Lt.data.BYTES_PER_ELEMENT);e.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,Z,0,0,St,Lt.width,Lt.height,1,Pt,Qt)}b.clearLayerUpdates()}else e.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,Z,0,0,0,Lt.width,Lt.height,dt.depth,Pt,Lt.data)}else e.compressedTexImage3D(i.TEXTURE_2D_ARRAY,Z,Yt,Lt.width,Lt.height,dt.depth,0,Lt.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else ee?z&&e.texSubImage3D(i.TEXTURE_2D_ARRAY,Z,0,0,0,Lt.width,Lt.height,dt.depth,Pt,Xt,Lt.data):e.texImage3D(i.TEXTURE_2D_ARRAY,Z,Yt,Lt.width,Lt.height,dt.depth,0,Pt,Xt,Lt.data)}else{ee&&ye&&e.texStorage2D(i.TEXTURE_2D,xt,Yt,he[0].width,he[0].height);for(let Z=0,at=he.length;Z<at;Z++)Lt=he[Z],b.format!==wn?Pt!==null?ee?z&&e.compressedTexSubImage2D(i.TEXTURE_2D,Z,0,0,Lt.width,Lt.height,Pt,Lt.data):e.compressedTexImage2D(i.TEXTURE_2D,Z,Yt,Lt.width,Lt.height,0,Lt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):ee?z&&e.texSubImage2D(i.TEXTURE_2D,Z,0,0,Lt.width,Lt.height,Pt,Xt,Lt.data):e.texImage2D(i.TEXTURE_2D,Z,Yt,Lt.width,Lt.height,0,Pt,Xt,Lt.data)}else if(b.isDataArrayTexture)if(ee){if(ye&&e.texStorage3D(i.TEXTURE_2D_ARRAY,xt,Yt,dt.width,dt.height,dt.depth),z)if(b.layerUpdates.size>0){const Z=lh(dt.width,dt.height,b.format,b.type);for(const at of b.layerUpdates){const Et=dt.data.subarray(at*Z/dt.data.BYTES_PER_ELEMENT,(at+1)*Z/dt.data.BYTES_PER_ELEMENT);e.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,at,dt.width,dt.height,1,Pt,Xt,Et)}b.clearLayerUpdates()}else e.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,0,dt.width,dt.height,dt.depth,Pt,Xt,dt.data)}else e.texImage3D(i.TEXTURE_2D_ARRAY,0,Yt,dt.width,dt.height,dt.depth,0,Pt,Xt,dt.data);else if(b.isData3DTexture)ee?(ye&&e.texStorage3D(i.TEXTURE_3D,xt,Yt,dt.width,dt.height,dt.depth),z&&e.texSubImage3D(i.TEXTURE_3D,0,0,0,0,dt.width,dt.height,dt.depth,Pt,Xt,dt.data)):e.texImage3D(i.TEXTURE_3D,0,Yt,dt.width,dt.height,dt.depth,0,Pt,Xt,dt.data);else if(b.isFramebufferTexture){if(ye)if(ee)e.texStorage2D(i.TEXTURE_2D,xt,Yt,dt.width,dt.height);else{let Z=dt.width,at=dt.height;for(let Et=0;Et<xt;Et++)e.texImage2D(i.TEXTURE_2D,Et,Yt,Z,at,0,Pt,Xt,null),Z>>=1,at>>=1}}else if(he.length>0){if(ee&&ye){const Z=Ht(he[0]);e.texStorage2D(i.TEXTURE_2D,xt,Yt,Z.width,Z.height)}for(let Z=0,at=he.length;Z<at;Z++)Lt=he[Z],ee?z&&e.texSubImage2D(i.TEXTURE_2D,Z,0,0,Pt,Xt,Lt):e.texImage2D(i.TEXTURE_2D,Z,Yt,Pt,Xt,Lt);b.generateMipmaps=!1}else if(ee){if(ye){const Z=Ht(dt);e.texStorage2D(i.TEXTURE_2D,xt,Yt,Z.width,Z.height)}z&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,Pt,Xt,dt)}else e.texImage2D(i.TEXTURE_2D,0,Yt,Pt,Xt,dt);m(b)&&d(ot),Ft.__version=rt.version,b.onUpdate&&b.onUpdate(b)}I.__version=b.version}function K(I,b,q){if(b.image.length!==6)return;const ot=wt(I,b),lt=b.source;e.bindTexture(i.TEXTURE_CUBE_MAP,I.__webglTexture,i.TEXTURE0+q);const rt=n.get(lt);if(lt.version!==rt.__version||ot===!0){e.activeTexture(i.TEXTURE0+q);const Ft=le.getPrimaries(le.workingColorSpace),Mt=b.colorSpace===Ei?null:le.getPrimaries(b.colorSpace),Ct=b.colorSpace===Ei||Ft===Mt?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,b.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,b.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,b.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,Ct);const de=b.isCompressedTexture||b.image[0].isCompressedTexture,dt=b.image[0]&&b.image[0].isDataTexture,Pt=[];for(let at=0;at<6;at++)!de&&!dt?Pt[at]=_(b.image[at],!0,s.maxCubemapSize):Pt[at]=dt?b.image[at].image:b.image[at],Pt[at]=Ae(b,Pt[at]);const Xt=Pt[0],Yt=r.convert(b.format,b.colorSpace),Lt=r.convert(b.type),he=T(b.internalFormat,Yt,Lt,b.colorSpace),ee=b.isVideoTexture!==!0,ye=rt.__version===void 0||ot===!0,z=lt.dataReady;let xt=F(b,Xt);Rt(i.TEXTURE_CUBE_MAP,b);let Z;if(de){ee&&ye&&e.texStorage2D(i.TEXTURE_CUBE_MAP,xt,he,Xt.width,Xt.height);for(let at=0;at<6;at++){Z=Pt[at].mipmaps;for(let Et=0;Et<Z.length;Et++){const St=Z[Et];b.format!==wn?Yt!==null?ee?z&&e.compressedTexSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et,0,0,St.width,St.height,Yt,St.data):e.compressedTexImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et,he,St.width,St.height,0,St.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):ee?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et,0,0,St.width,St.height,Yt,Lt,St.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et,he,St.width,St.height,0,Yt,Lt,St.data)}}}else{if(Z=b.mipmaps,ee&&ye){Z.length>0&&xt++;const at=Ht(Pt[0]);e.texStorage2D(i.TEXTURE_CUBE_MAP,xt,he,at.width,at.height)}for(let at=0;at<6;at++)if(dt){ee?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,0,0,0,Pt[at].width,Pt[at].height,Yt,Lt,Pt[at].data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,0,he,Pt[at].width,Pt[at].height,0,Yt,Lt,Pt[at].data);for(let Et=0;Et<Z.length;Et++){const Qt=Z[Et].image[at].image;ee?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et+1,0,0,Qt.width,Qt.height,Yt,Lt,Qt.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et+1,he,Qt.width,Qt.height,0,Yt,Lt,Qt.data)}}else{ee?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,0,0,0,Yt,Lt,Pt[at]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,0,he,Yt,Lt,Pt[at]);for(let Et=0;Et<Z.length;Et++){const St=Z[Et];ee?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et+1,0,0,Yt,Lt,St.image[at]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+at,Et+1,he,Yt,Lt,St.image[at])}}}m(b)&&d(i.TEXTURE_CUBE_MAP),rt.__version=lt.version,b.onUpdate&&b.onUpdate(b)}I.__version=b.version}function nt(I,b,q,ot,lt,rt){const Ft=r.convert(q.format,q.colorSpace),Mt=r.convert(q.type),Ct=T(q.internalFormat,Ft,Mt,q.colorSpace),de=n.get(b),dt=n.get(q);if(dt.__renderTarget=b,!de.__hasExternalTextures){const Pt=Math.max(1,b.width>>rt),Xt=Math.max(1,b.height>>rt);lt===i.TEXTURE_3D||lt===i.TEXTURE_2D_ARRAY?e.texImage3D(lt,rt,Ct,Pt,Xt,b.depth,0,Ft,Mt,null):e.texImage2D(lt,rt,Ct,Pt,Xt,0,Ft,Mt,null)}e.bindFramebuffer(i.FRAMEBUFFER,I),ce(b)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,ot,lt,dt.__webglTexture,0,ae(b)):(lt===i.TEXTURE_2D||lt>=i.TEXTURE_CUBE_MAP_POSITIVE_X&&lt<=i.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&i.framebufferTexture2D(i.FRAMEBUFFER,ot,lt,dt.__webglTexture,rt),e.bindFramebuffer(i.FRAMEBUFFER,null)}function it(I,b,q){if(i.bindRenderbuffer(i.RENDERBUFFER,I),b.depthBuffer){const ot=b.depthTexture,lt=ot&&ot.isDepthTexture?ot.type:null,rt=M(b.stencilBuffer,lt),Ft=b.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,Mt=ae(b);ce(b)?o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,Mt,rt,b.width,b.height):q?i.renderbufferStorageMultisample(i.RENDERBUFFER,Mt,rt,b.width,b.height):i.renderbufferStorage(i.RENDERBUFFER,rt,b.width,b.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,Ft,i.RENDERBUFFER,I)}else{const ot=b.textures;for(let lt=0;lt<ot.length;lt++){const rt=ot[lt],Ft=r.convert(rt.format,rt.colorSpace),Mt=r.convert(rt.type),Ct=T(rt.internalFormat,Ft,Mt,rt.colorSpace),de=ae(b);q&&ce(b)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,de,Ct,b.width,b.height):ce(b)?o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,de,Ct,b.width,b.height):i.renderbufferStorage(i.RENDERBUFFER,Ct,b.width,b.height)}}i.bindRenderbuffer(i.RENDERBUFFER,null)}function vt(I,b){if(b&&b.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(e.bindFramebuffer(i.FRAMEBUFFER,I),!(b.depthTexture&&b.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");const ot=n.get(b.depthTexture);ot.__renderTarget=b,(!ot.__webglTexture||b.depthTexture.image.width!==b.width||b.depthTexture.image.height!==b.height)&&(b.depthTexture.image.width=b.width,b.depthTexture.image.height=b.height,b.depthTexture.needsUpdate=!0),Q(b.depthTexture,0);const lt=ot.__webglTexture,rt=ae(b);if(b.depthTexture.format===xs)ce(b)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,lt,0,rt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,lt,0);else if(b.depthTexture.format===Rs)ce(b)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,lt,0,rt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,lt,0);else throw new Error("Unknown depthTexture format")}function zt(I){const b=n.get(I),q=I.isWebGLCubeRenderTarget===!0;if(b.__boundDepthTexture!==I.depthTexture){const ot=I.depthTexture;if(b.__depthDisposeCallback&&b.__depthDisposeCallback(),ot){const lt=()=>{delete b.__boundDepthTexture,delete b.__depthDisposeCallback,ot.removeEventListener("dispose",lt)};ot.addEventListener("dispose",lt),b.__depthDisposeCallback=lt}b.__boundDepthTexture=ot}if(I.depthTexture&&!b.__autoAllocateDepthBuffer){if(q)throw new Error("target.depthTexture not supported in Cube render targets");vt(b.__webglFramebuffer,I)}else if(q){b.__webglDepthbuffer=[];for(let ot=0;ot<6;ot++)if(e.bindFramebuffer(i.FRAMEBUFFER,b.__webglFramebuffer[ot]),b.__webglDepthbuffer[ot]===void 0)b.__webglDepthbuffer[ot]=i.createRenderbuffer(),it(b.__webglDepthbuffer[ot],I,!1);else{const lt=I.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,rt=b.__webglDepthbuffer[ot];i.bindRenderbuffer(i.RENDERBUFFER,rt),i.framebufferRenderbuffer(i.FRAMEBUFFER,lt,i.RENDERBUFFER,rt)}}else if(e.bindFramebuffer(i.FRAMEBUFFER,b.__webglFramebuffer),b.__webglDepthbuffer===void 0)b.__webglDepthbuffer=i.createRenderbuffer(),it(b.__webglDepthbuffer,I,!1);else{const ot=I.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,lt=b.__webglDepthbuffer;i.bindRenderbuffer(i.RENDERBUFFER,lt),i.framebufferRenderbuffer(i.FRAMEBUFFER,ot,i.RENDERBUFFER,lt)}e.bindFramebuffer(i.FRAMEBUFFER,null)}function Zt(I,b,q){const ot=n.get(I);b!==void 0&&nt(ot.__webglFramebuffer,I,I.texture,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,0),q!==void 0&&zt(I)}function Ce(I){const b=I.texture,q=n.get(I),ot=n.get(b);I.addEventListener("dispose",N);const lt=I.textures,rt=I.isWebGLCubeRenderTarget===!0,Ft=lt.length>1;if(Ft||(ot.__webglTexture===void 0&&(ot.__webglTexture=i.createTexture()),ot.__version=b.version,a.memory.textures++),rt){q.__webglFramebuffer=[];for(let Mt=0;Mt<6;Mt++)if(b.mipmaps&&b.mipmaps.length>0){q.__webglFramebuffer[Mt]=[];for(let Ct=0;Ct<b.mipmaps.length;Ct++)q.__webglFramebuffer[Mt][Ct]=i.createFramebuffer()}else q.__webglFramebuffer[Mt]=i.createFramebuffer()}else{if(b.mipmaps&&b.mipmaps.length>0){q.__webglFramebuffer=[];for(let Mt=0;Mt<b.mipmaps.length;Mt++)q.__webglFramebuffer[Mt]=i.createFramebuffer()}else q.__webglFramebuffer=i.createFramebuffer();if(Ft)for(let Mt=0,Ct=lt.length;Mt<Ct;Mt++){const de=n.get(lt[Mt]);de.__webglTexture===void 0&&(de.__webglTexture=i.createTexture(),a.memory.textures++)}if(I.samples>0&&ce(I)===!1){q.__webglMultisampledFramebuffer=i.createFramebuffer(),q.__webglColorRenderbuffer=[],e.bindFramebuffer(i.FRAMEBUFFER,q.__webglMultisampledFramebuffer);for(let Mt=0;Mt<lt.length;Mt++){const Ct=lt[Mt];q.__webglColorRenderbuffer[Mt]=i.createRenderbuffer(),i.bindRenderbuffer(i.RENDERBUFFER,q.__webglColorRenderbuffer[Mt]);const de=r.convert(Ct.format,Ct.colorSpace),dt=r.convert(Ct.type),Pt=T(Ct.internalFormat,de,dt,Ct.colorSpace,I.isXRRenderTarget===!0),Xt=ae(I);i.renderbufferStorageMultisample(i.RENDERBUFFER,Xt,Pt,I.width,I.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Mt,i.RENDERBUFFER,q.__webglColorRenderbuffer[Mt])}i.bindRenderbuffer(i.RENDERBUFFER,null),I.depthBuffer&&(q.__webglDepthRenderbuffer=i.createRenderbuffer(),it(q.__webglDepthRenderbuffer,I,!0)),e.bindFramebuffer(i.FRAMEBUFFER,null)}}if(rt){e.bindTexture(i.TEXTURE_CUBE_MAP,ot.__webglTexture),Rt(i.TEXTURE_CUBE_MAP,b);for(let Mt=0;Mt<6;Mt++)if(b.mipmaps&&b.mipmaps.length>0)for(let Ct=0;Ct<b.mipmaps.length;Ct++)nt(q.__webglFramebuffer[Mt][Ct],I,b,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+Mt,Ct);else nt(q.__webglFramebuffer[Mt],I,b,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+Mt,0);m(b)&&d(i.TEXTURE_CUBE_MAP),e.unbindTexture()}else if(Ft){for(let Mt=0,Ct=lt.length;Mt<Ct;Mt++){const de=lt[Mt],dt=n.get(de);e.bindTexture(i.TEXTURE_2D,dt.__webglTexture),Rt(i.TEXTURE_2D,de),nt(q.__webglFramebuffer,I,de,i.COLOR_ATTACHMENT0+Mt,i.TEXTURE_2D,0),m(de)&&d(i.TEXTURE_2D)}e.unbindTexture()}else{let Mt=i.TEXTURE_2D;if((I.isWebGL3DRenderTarget||I.isWebGLArrayRenderTarget)&&(Mt=I.isWebGL3DRenderTarget?i.TEXTURE_3D:i.TEXTURE_2D_ARRAY),e.bindTexture(Mt,ot.__webglTexture),Rt(Mt,b),b.mipmaps&&b.mipmaps.length>0)for(let Ct=0;Ct<b.mipmaps.length;Ct++)nt(q.__webglFramebuffer[Ct],I,b,i.COLOR_ATTACHMENT0,Mt,Ct);else nt(q.__webglFramebuffer,I,b,i.COLOR_ATTACHMENT0,Mt,0);m(b)&&d(Mt),e.unbindTexture()}I.depthBuffer&&zt(I)}function ue(I){const b=I.textures;for(let q=0,ot=b.length;q<ot;q++){const lt=b[q];if(m(lt)){const rt=w(I),Ft=n.get(lt).__webglTexture;e.bindTexture(rt,Ft),d(rt),e.unbindTexture()}}}const De=[],G=[];function on(I){if(I.samples>0){if(ce(I)===!1){const b=I.textures,q=I.width,ot=I.height;let lt=i.COLOR_BUFFER_BIT;const rt=I.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,Ft=n.get(I),Mt=b.length>1;if(Mt)for(let Ct=0;Ct<b.length;Ct++)e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.RENDERBUFFER,null),e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.TEXTURE_2D,null,0);e.bindFramebuffer(i.READ_FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,Ft.__webglFramebuffer);for(let Ct=0;Ct<b.length;Ct++){if(I.resolveDepthBuffer&&(I.depthBuffer&&(lt|=i.DEPTH_BUFFER_BIT),I.stencilBuffer&&I.resolveStencilBuffer&&(lt|=i.STENCIL_BUFFER_BIT)),Mt){i.framebufferRenderbuffer(i.READ_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.RENDERBUFFER,Ft.__webglColorRenderbuffer[Ct]);const de=n.get(b[Ct]).__webglTexture;i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,de,0)}i.blitFramebuffer(0,0,q,ot,0,0,q,ot,lt,i.NEAREST),c===!0&&(De.length=0,G.length=0,De.push(i.COLOR_ATTACHMENT0+Ct),I.depthBuffer&&I.resolveDepthBuffer===!1&&(De.push(rt),G.push(rt),i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,G)),i.invalidateFramebuffer(i.READ_FRAMEBUFFER,De))}if(e.bindFramebuffer(i.READ_FRAMEBUFFER,null),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),Mt)for(let Ct=0;Ct<b.length;Ct++){e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.RENDERBUFFER,Ft.__webglColorRenderbuffer[Ct]);const de=n.get(b[Ct]).__webglTexture;e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.TEXTURE_2D,de,0)}e.bindFramebuffer(i.DRAW_FRAMEBUFFER,Ft.__webglMultisampledFramebuffer)}else if(I.depthBuffer&&I.resolveDepthBuffer===!1&&c){const b=I.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT;i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,[b])}}}function ae(I){return Math.min(s.maxSamples,I.samples)}function ce(I){const b=n.get(I);return I.samples>0&&t.has("WEBGL_multisampled_render_to_texture")===!0&&b.__useRenderToTexture!==!1}function Wt(I){const b=a.render.frame;h.get(I)!==b&&(h.set(I,b),I.update())}function Ae(I,b){const q=I.colorSpace,ot=I.format,lt=I.type;return I.isCompressedTexture===!0||I.isVideoTexture===!0||q!==Us&&q!==Ei&&(le.getTransfer(q)===Ee?(ot!==wn||lt!==ci)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",q)),b}function Ht(I){return typeof HTMLImageElement<"u"&&I instanceof HTMLImageElement?(l.width=I.naturalWidth||I.width,l.height=I.naturalHeight||I.height):typeof VideoFrame<"u"&&I instanceof VideoFrame?(l.width=I.displayWidth,l.height=I.displayHeight):(l.width=I.width,l.height=I.height),l}this.allocateTextureUnit=H,this.resetTextureUnits=k,this.setTexture2D=Q,this.setTexture2DArray=O,this.setTexture3D=tt,this.setTextureCube=W,this.rebindTextures=Zt,this.setupRenderTarget=Ce,this.updateRenderTargetMipmap=ue,this.updateMultisampleRenderTarget=on,this.setupDepthRenderbuffer=zt,this.setupFrameBufferTexture=nt,this.useMultisampledRTT=ce}function w0(i,t){function e(n,s=Ei){let r;const a=le.getTransfer(s);if(n===ci)return i.UNSIGNED_BYTE;if(n===Oc)return i.UNSIGNED_SHORT_4_4_4_4;if(n===kc)return i.UNSIGNED_SHORT_5_5_5_1;if(n===tu)return i.UNSIGNED_INT_5_9_9_9_REV;if(n===Zh)return i.BYTE;if(n===Qh)return i.SHORT;if(n===cr)return i.UNSIGNED_SHORT;if(n===Fc)return i.INT;if(n===Xi)return i.UNSIGNED_INT;if(n===Wn)return i.FLOAT;if(n===gr)return i.HALF_FLOAT;if(n===eu)return i.ALPHA;if(n===nu)return i.RGB;if(n===wn)return i.RGBA;if(n===iu)return i.LUMINANCE;if(n===su)return i.LUMINANCE_ALPHA;if(n===xs)return i.DEPTH_COMPONENT;if(n===Rs)return i.DEPTH_STENCIL;if(n===ru)return i.RED;if(n===Bc)return i.RED_INTEGER;if(n===ou)return i.RG;if(n===zc)return i.RG_INTEGER;if(n===Vc)return i.RGBA_INTEGER;if(n===ho||n===uo||n===fo||n===po)if(a===Ee)if(r=t.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(n===ho)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===uo)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===fo)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===po)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=t.get("WEBGL_compressed_texture_s3tc"),r!==null){if(n===ho)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===uo)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===fo)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===po)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===Qa||n===tc||n===ec||n===nc)if(r=t.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(n===Qa)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===tc)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===ec)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===nc)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===ic||n===sc||n===rc)if(r=t.get("WEBGL_compressed_texture_etc"),r!==null){if(n===ic||n===sc)return a===Ee?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(n===rc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(n===oc||n===ac||n===cc||n===lc||n===hc||n===uc||n===dc||n===fc||n===pc||n===mc||n===gc||n===_c||n===vc||n===xc)if(r=t.get("WEBGL_compressed_texture_astc"),r!==null){if(n===oc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===ac)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===cc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===lc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===hc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===uc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===dc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===fc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===pc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===mc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===gc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===_c)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===vc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===xc)return a===Ee?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===mo||n===yc||n===Mc)if(r=t.get("EXT_texture_compression_bptc"),r!==null){if(n===mo)return a===Ee?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===yc)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===Mc)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===au||n===Sc||n===bc||n===Ec)if(r=t.get("EXT_texture_compression_rgtc"),r!==null){if(n===mo)return r.COMPRESSED_RED_RGTC1_EXT;if(n===Sc)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===bc)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===Ec)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===Cs?i.UNSIGNED_INT_24_8:i[n]!==void 0?i[n]:null}return{convert:e}}class T0 extends Je{constructor(t=[]){super(),this.isArrayCamera=!0,this.cameras=t}}class Fe extends Ne{constructor(){super(),this.isGroup=!0,this.type="Group"}}const A0={type:"move"};class wa{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Fe,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Fe,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new L,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new L),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Fe,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new L,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new L),this._grip}dispatchEvent(t){return this._targetRay!==null&&this._targetRay.dispatchEvent(t),this._grip!==null&&this._grip.dispatchEvent(t),this._hand!==null&&this._hand.dispatchEvent(t),this}connect(t){if(t&&t.hand){const e=this._hand;if(e)for(const n of t.hand.values())this._getHandJoint(e,n)}return this.dispatchEvent({type:"connected",data:t}),this}disconnect(t){return this.dispatchEvent({type:"disconnected",data:t}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(t,e,n){let s=null,r=null,a=null;const o=this._targetRay,c=this._grip,l=this._hand;if(t&&e.session.visibilityState!=="visible-blurred"){if(l&&t.hand){a=!0;for(const _ of t.hand.values()){const m=e.getJointPose(_,n),d=this._getHandJoint(l,_);m!==null&&(d.matrix.fromArray(m.transform.matrix),d.matrix.decompose(d.position,d.rotation,d.scale),d.matrixWorldNeedsUpdate=!0,d.jointRadius=m.radius),d.visible=m!==null}const h=l.joints["index-finger-tip"],u=l.joints["thumb-tip"],f=h.position.distanceTo(u.position),p=.02,g=.005;l.inputState.pinching&&f>p+g?(l.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:t.handedness,target:this})):!l.inputState.pinching&&f<=p-g&&(l.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:t.handedness,target:this}))}else c!==null&&t.gripSpace&&(r=e.getPose(t.gripSpace,n),r!==null&&(c.matrix.fromArray(r.transform.matrix),c.matrix.decompose(c.position,c.rotation,c.scale),c.matrixWorldNeedsUpdate=!0,r.linearVelocity?(c.hasLinearVelocity=!0,c.linearVelocity.copy(r.linearVelocity)):c.hasLinearVelocity=!1,r.angularVelocity?(c.hasAngularVelocity=!0,c.angularVelocity.copy(r.angularVelocity)):c.hasAngularVelocity=!1));o!==null&&(s=e.getPose(t.targetRaySpace,n),s===null&&r!==null&&(s=r),s!==null&&(o.matrix.fromArray(s.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,s.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(s.linearVelocity)):o.hasLinearVelocity=!1,s.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(s.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(A0)))}return o!==null&&(o.visible=s!==null),c!==null&&(c.visible=r!==null),l!==null&&(l.visible=a!==null),this}_getHandJoint(t,e){if(t.joints[e.jointName]===void 0){const n=new Fe;n.matrixAutoUpdate=!1,n.visible=!1,t.joints[e.jointName]=n,t.add(n)}return t.joints[e.jointName]}}const C0=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,R0=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;class P0{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(t,e,n){if(this.texture===null){const s=new Ye,r=t.properties.get(s);r.__webglTexture=e.texture,(e.depthNear!=n.depthNear||e.depthFar!=n.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=s}}getMesh(t){if(this.texture!==null&&this.mesh===null){const e=t.cameras[0].viewport,n=new Ci({vertexShader:C0,fragmentShader:R0,uniforms:{depthColor:{value:this.texture},depthWidth:{value:e.z},depthHeight:{value:e.w}}});this.mesh=new me(new Bo(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}}class L0 extends $i{constructor(t,e){super();const n=this;let s=null,r=1,a=null,o="local-floor",c=1,l=null,h=null,u=null,f=null,p=null,g=null;const _=new P0,m=e.getContextAttributes();let d=null,w=null;const T=[],M=[],F=new At;let P=null;const N=new Je;N.viewport=new xe;const D=new Je;D.viewport=new xe;const y=[N,D],S=new T0;let U=null,k=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(X){let K=T[X];return K===void 0&&(K=new wa,T[X]=K),K.getTargetRaySpace()},this.getControllerGrip=function(X){let K=T[X];return K===void 0&&(K=new wa,T[X]=K),K.getGripSpace()},this.getHand=function(X){let K=T[X];return K===void 0&&(K=new wa,T[X]=K),K.getHandSpace()};function H(X){const K=M.indexOf(X.inputSource);if(K===-1)return;const nt=T[K];nt!==void 0&&(nt.update(X.inputSource,X.frame,l||a),nt.dispatchEvent({type:X.type,data:X.inputSource}))}function J(){s.removeEventListener("select",H),s.removeEventListener("selectstart",H),s.removeEventListener("selectend",H),s.removeEventListener("squeeze",H),s.removeEventListener("squeezestart",H),s.removeEventListener("squeezeend",H),s.removeEventListener("end",J),s.removeEventListener("inputsourceschange",Q);for(let X=0;X<T.length;X++){const K=M[X];K!==null&&(M[X]=null,T[X].disconnect(K))}U=null,k=null,_.reset(),t.setRenderTarget(d),p=null,f=null,u=null,s=null,w=null,wt.stop(),n.isPresenting=!1,t.setPixelRatio(P),t.setSize(F.width,F.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(X){r=X,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(X){o=X,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return l||a},this.setReferenceSpace=function(X){l=X},this.getBaseLayer=function(){return f!==null?f:p},this.getBinding=function(){return u},this.getFrame=function(){return g},this.getSession=function(){return s},this.setSession=async function(X){if(s=X,s!==null){if(d=t.getRenderTarget(),s.addEventListener("select",H),s.addEventListener("selectstart",H),s.addEventListener("selectend",H),s.addEventListener("squeeze",H),s.addEventListener("squeezestart",H),s.addEventListener("squeezeend",H),s.addEventListener("end",J),s.addEventListener("inputsourceschange",Q),m.xrCompatible!==!0&&await e.makeXRCompatible(),P=t.getPixelRatio(),t.getSize(F),s.renderState.layers===void 0){const K={antialias:m.antialias,alpha:!0,depth:m.depth,stencil:m.stencil,framebufferScaleFactor:r};p=new XRWebGLLayer(s,e,K),s.updateRenderState({baseLayer:p}),t.setPixelRatio(1),t.setSize(p.framebufferWidth,p.framebufferHeight,!1),w=new qi(p.framebufferWidth,p.framebufferHeight,{format:wn,type:ci,colorSpace:t.outputColorSpace,stencilBuffer:m.stencil})}else{let K=null,nt=null,it=null;m.depth&&(it=m.stencil?e.DEPTH24_STENCIL8:e.DEPTH_COMPONENT24,K=m.stencil?Rs:xs,nt=m.stencil?Cs:Xi);const vt={colorFormat:e.RGBA8,depthFormat:it,scaleFactor:r};u=new XRWebGLBinding(s,e),f=u.createProjectionLayer(vt),s.updateRenderState({layers:[f]}),t.setPixelRatio(1),t.setSize(f.textureWidth,f.textureHeight,!1),w=new qi(f.textureWidth,f.textureHeight,{format:wn,type:ci,depthTexture:new xu(f.textureWidth,f.textureHeight,nt,void 0,void 0,void 0,void 0,void 0,void 0,K),stencilBuffer:m.stencil,colorSpace:t.outputColorSpace,samples:m.antialias?4:0,resolveDepthBuffer:f.ignoreDepthValues===!1})}w.isXRRenderTarget=!0,this.setFoveation(c),l=null,a=await s.requestReferenceSpace(o),wt.setContext(s),wt.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(s!==null)return s.environmentBlendMode},this.getDepthTexture=function(){return _.getDepthTexture()};function Q(X){for(let K=0;K<X.removed.length;K++){const nt=X.removed[K],it=M.indexOf(nt);it>=0&&(M[it]=null,T[it].disconnect(nt))}for(let K=0;K<X.added.length;K++){const nt=X.added[K];let it=M.indexOf(nt);if(it===-1){for(let zt=0;zt<T.length;zt++)if(zt>=M.length){M.push(nt),it=zt;break}else if(M[zt]===null){M[zt]=nt,it=zt;break}if(it===-1)break}const vt=T[it];vt&&vt.connect(nt)}}const O=new L,tt=new L;function W(X,K,nt){O.setFromMatrixPosition(K.matrixWorld),tt.setFromMatrixPosition(nt.matrixWorld);const it=O.distanceTo(tt),vt=K.projectionMatrix.elements,zt=nt.projectionMatrix.elements,Zt=vt[14]/(vt[10]-1),Ce=vt[14]/(vt[10]+1),ue=(vt[9]+1)/vt[5],De=(vt[9]-1)/vt[5],G=(vt[8]-1)/vt[0],on=(zt[8]+1)/zt[0],ae=Zt*G,ce=Zt*on,Wt=it/(-G+on),Ae=Wt*-G;if(K.matrixWorld.decompose(X.position,X.quaternion,X.scale),X.translateX(Ae),X.translateZ(Wt),X.matrixWorld.compose(X.position,X.quaternion,X.scale),X.matrixWorldInverse.copy(X.matrixWorld).invert(),vt[10]===-1)X.projectionMatrix.copy(K.projectionMatrix),X.projectionMatrixInverse.copy(K.projectionMatrixInverse);else{const Ht=Zt+Wt,I=Ce+Wt,b=ae-Ae,q=ce+(it-Ae),ot=ue*Ce/I*Ht,lt=De*Ce/I*Ht;X.projectionMatrix.makePerspective(b,q,ot,lt,Ht,I),X.projectionMatrixInverse.copy(X.projectionMatrix).invert()}}function ct(X,K){K===null?X.matrixWorld.copy(X.matrix):X.matrixWorld.multiplyMatrices(K.matrixWorld,X.matrix),X.matrixWorldInverse.copy(X.matrixWorld).invert()}this.updateCamera=function(X){if(s===null)return;let K=X.near,nt=X.far;_.texture!==null&&(_.depthNear>0&&(K=_.depthNear),_.depthFar>0&&(nt=_.depthFar)),S.near=D.near=N.near=K,S.far=D.far=N.far=nt,(U!==S.near||k!==S.far)&&(s.updateRenderState({depthNear:S.near,depthFar:S.far}),U=S.near,k=S.far),N.layers.mask=X.layers.mask|2,D.layers.mask=X.layers.mask|4,S.layers.mask=N.layers.mask|D.layers.mask;const it=X.parent,vt=S.cameras;ct(S,it);for(let zt=0;zt<vt.length;zt++)ct(vt[zt],it);vt.length===2?W(S,N,D):S.projectionMatrix.copy(N.projectionMatrix),ft(X,S,it)};function ft(X,K,nt){nt===null?X.matrix.copy(K.matrixWorld):(X.matrix.copy(nt.matrixWorld),X.matrix.invert(),X.matrix.multiply(K.matrixWorld)),X.matrix.decompose(X.position,X.quaternion,X.scale),X.updateMatrixWorld(!0),X.projectionMatrix.copy(K.projectionMatrix),X.projectionMatrixInverse.copy(K.projectionMatrixInverse),X.isPerspectiveCamera&&(X.fov=Ps*2*Math.atan(1/X.projectionMatrix.elements[5]),X.zoom=1)}this.getCamera=function(){return S},this.getFoveation=function(){if(!(f===null&&p===null))return c},this.setFoveation=function(X){c=X,f!==null&&(f.fixedFoveation=X),p!==null&&p.fixedFoveation!==void 0&&(p.fixedFoveation=X)},this.hasDepthSensing=function(){return _.texture!==null},this.getDepthSensingMesh=function(){return _.getMesh(S)};let pt=null;function Rt(X,K){if(h=K.getViewerPose(l||a),g=K,h!==null){const nt=h.views;p!==null&&(t.setRenderTargetFramebuffer(w,p.framebuffer),t.setRenderTarget(w));let it=!1;nt.length!==S.cameras.length&&(S.cameras.length=0,it=!0);for(let zt=0;zt<nt.length;zt++){const Zt=nt[zt];let Ce=null;if(p!==null)Ce=p.getViewport(Zt);else{const De=u.getViewSubImage(f,Zt);Ce=De.viewport,zt===0&&(t.setRenderTargetTextures(w,De.colorTexture,f.ignoreDepthValues?void 0:De.depthStencilTexture),t.setRenderTarget(w))}let ue=y[zt];ue===void 0&&(ue=new Je,ue.layers.enable(zt),ue.viewport=new xe,y[zt]=ue),ue.matrix.fromArray(Zt.transform.matrix),ue.matrix.decompose(ue.position,ue.quaternion,ue.scale),ue.projectionMatrix.fromArray(Zt.projectionMatrix),ue.projectionMatrixInverse.copy(ue.projectionMatrix).invert(),ue.viewport.set(Ce.x,Ce.y,Ce.width,Ce.height),zt===0&&(S.matrix.copy(ue.matrix),S.matrix.decompose(S.position,S.quaternion,S.scale)),it===!0&&S.cameras.push(ue)}const vt=s.enabledFeatures;if(vt&&vt.includes("depth-sensing")){const zt=u.getDepthInformation(nt[0]);zt&&zt.isValid&&zt.texture&&_.init(t,zt,s.renderState)}}for(let nt=0;nt<T.length;nt++){const it=M[nt],vt=T[nt];it!==null&&vt!==void 0&&vt.update(it,K,l||a)}pt&&pt(X,K),K.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:K}),g=null}const wt=new vu;wt.setAnimationLoop(Rt),this.setAnimationLoop=function(X){pt=X},this.dispose=function(){}}}const Bi=new fn,N0=new jt;function D0(i,t){function e(m,d){m.matrixAutoUpdate===!0&&m.updateMatrix(),d.value.copy(m.matrix)}function n(m,d){d.color.getRGB(m.fogColor.value,mu(i)),d.isFog?(m.fogNear.value=d.near,m.fogFar.value=d.far):d.isFogExp2&&(m.fogDensity.value=d.density)}function s(m,d,w,T,M){d.isMeshBasicMaterial||d.isMeshLambertMaterial?r(m,d):d.isMeshToonMaterial?(r(m,d),u(m,d)):d.isMeshPhongMaterial?(r(m,d),h(m,d)):d.isMeshStandardMaterial?(r(m,d),f(m,d),d.isMeshPhysicalMaterial&&p(m,d,M)):d.isMeshMatcapMaterial?(r(m,d),g(m,d)):d.isMeshDepthMaterial?r(m,d):d.isMeshDistanceMaterial?(r(m,d),_(m,d)):d.isMeshNormalMaterial?r(m,d):d.isLineBasicMaterial?(a(m,d),d.isLineDashedMaterial&&o(m,d)):d.isPointsMaterial?c(m,d,w,T):d.isSpriteMaterial?l(m,d):d.isShadowMaterial?(m.color.value.copy(d.color),m.opacity.value=d.opacity):d.isShaderMaterial&&(d.uniformsNeedUpdate=!1)}function r(m,d){m.opacity.value=d.opacity,d.color&&m.diffuse.value.copy(d.color),d.emissive&&m.emissive.value.copy(d.emissive).multiplyScalar(d.emissiveIntensity),d.map&&(m.map.value=d.map,e(d.map,m.mapTransform)),d.alphaMap&&(m.alphaMap.value=d.alphaMap,e(d.alphaMap,m.alphaMapTransform)),d.bumpMap&&(m.bumpMap.value=d.bumpMap,e(d.bumpMap,m.bumpMapTransform),m.bumpScale.value=d.bumpScale,d.side===dn&&(m.bumpScale.value*=-1)),d.normalMap&&(m.normalMap.value=d.normalMap,e(d.normalMap,m.normalMapTransform),m.normalScale.value.copy(d.normalScale),d.side===dn&&m.normalScale.value.negate()),d.displacementMap&&(m.displacementMap.value=d.displacementMap,e(d.displacementMap,m.displacementMapTransform),m.displacementScale.value=d.displacementScale,m.displacementBias.value=d.displacementBias),d.emissiveMap&&(m.emissiveMap.value=d.emissiveMap,e(d.emissiveMap,m.emissiveMapTransform)),d.specularMap&&(m.specularMap.value=d.specularMap,e(d.specularMap,m.specularMapTransform)),d.alphaTest>0&&(m.alphaTest.value=d.alphaTest);const w=t.get(d),T=w.envMap,M=w.envMapRotation;T&&(m.envMap.value=T,Bi.copy(M),Bi.x*=-1,Bi.y*=-1,Bi.z*=-1,T.isCubeTexture&&T.isRenderTargetTexture===!1&&(Bi.y*=-1,Bi.z*=-1),m.envMapRotation.value.setFromMatrix4(N0.makeRotationFromEuler(Bi)),m.flipEnvMap.value=T.isCubeTexture&&T.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=d.reflectivity,m.ior.value=d.ior,m.refractionRatio.value=d.refractionRatio),d.lightMap&&(m.lightMap.value=d.lightMap,m.lightMapIntensity.value=d.lightMapIntensity,e(d.lightMap,m.lightMapTransform)),d.aoMap&&(m.aoMap.value=d.aoMap,m.aoMapIntensity.value=d.aoMapIntensity,e(d.aoMap,m.aoMapTransform))}function a(m,d){m.diffuse.value.copy(d.color),m.opacity.value=d.opacity,d.map&&(m.map.value=d.map,e(d.map,m.mapTransform))}function o(m,d){m.dashSize.value=d.dashSize,m.totalSize.value=d.dashSize+d.gapSize,m.scale.value=d.scale}function c(m,d,w,T){m.diffuse.value.copy(d.color),m.opacity.value=d.opacity,m.size.value=d.size*w,m.scale.value=T*.5,d.map&&(m.map.value=d.map,e(d.map,m.uvTransform)),d.alphaMap&&(m.alphaMap.value=d.alphaMap,e(d.alphaMap,m.alphaMapTransform)),d.alphaTest>0&&(m.alphaTest.value=d.alphaTest)}function l(m,d){m.diffuse.value.copy(d.color),m.opacity.value=d.opacity,m.rotation.value=d.rotation,d.map&&(m.map.value=d.map,e(d.map,m.mapTransform)),d.alphaMap&&(m.alphaMap.value=d.alphaMap,e(d.alphaMap,m.alphaMapTransform)),d.alphaTest>0&&(m.alphaTest.value=d.alphaTest)}function h(m,d){m.specular.value.copy(d.specular),m.shininess.value=Math.max(d.shininess,1e-4)}function u(m,d){d.gradientMap&&(m.gradientMap.value=d.gradientMap)}function f(m,d){m.metalness.value=d.metalness,d.metalnessMap&&(m.metalnessMap.value=d.metalnessMap,e(d.metalnessMap,m.metalnessMapTransform)),m.roughness.value=d.roughness,d.roughnessMap&&(m.roughnessMap.value=d.roughnessMap,e(d.roughnessMap,m.roughnessMapTransform)),d.envMap&&(m.envMapIntensity.value=d.envMapIntensity)}function p(m,d,w){m.ior.value=d.ior,d.sheen>0&&(m.sheenColor.value.copy(d.sheenColor).multiplyScalar(d.sheen),m.sheenRoughness.value=d.sheenRoughness,d.sheenColorMap&&(m.sheenColorMap.value=d.sheenColorMap,e(d.sheenColorMap,m.sheenColorMapTransform)),d.sheenRoughnessMap&&(m.sheenRoughnessMap.value=d.sheenRoughnessMap,e(d.sheenRoughnessMap,m.sheenRoughnessMapTransform))),d.clearcoat>0&&(m.clearcoat.value=d.clearcoat,m.clearcoatRoughness.value=d.clearcoatRoughness,d.clearcoatMap&&(m.clearcoatMap.value=d.clearcoatMap,e(d.clearcoatMap,m.clearcoatMapTransform)),d.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=d.clearcoatRoughnessMap,e(d.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),d.clearcoatNormalMap&&(m.clearcoatNormalMap.value=d.clearcoatNormalMap,e(d.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(d.clearcoatNormalScale),d.side===dn&&m.clearcoatNormalScale.value.negate())),d.dispersion>0&&(m.dispersion.value=d.dispersion),d.iridescence>0&&(m.iridescence.value=d.iridescence,m.iridescenceIOR.value=d.iridescenceIOR,m.iridescenceThicknessMinimum.value=d.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=d.iridescenceThicknessRange[1],d.iridescenceMap&&(m.iridescenceMap.value=d.iridescenceMap,e(d.iridescenceMap,m.iridescenceMapTransform)),d.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=d.iridescenceThicknessMap,e(d.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),d.transmission>0&&(m.transmission.value=d.transmission,m.transmissionSamplerMap.value=w.texture,m.transmissionSamplerSize.value.set(w.width,w.height),d.transmissionMap&&(m.transmissionMap.value=d.transmissionMap,e(d.transmissionMap,m.transmissionMapTransform)),m.thickness.value=d.thickness,d.thicknessMap&&(m.thicknessMap.value=d.thicknessMap,e(d.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=d.attenuationDistance,m.attenuationColor.value.copy(d.attenuationColor)),d.anisotropy>0&&(m.anisotropyVector.value.set(d.anisotropy*Math.cos(d.anisotropyRotation),d.anisotropy*Math.sin(d.anisotropyRotation)),d.anisotropyMap&&(m.anisotropyMap.value=d.anisotropyMap,e(d.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=d.specularIntensity,m.specularColor.value.copy(d.specularColor),d.specularColorMap&&(m.specularColorMap.value=d.specularColorMap,e(d.specularColorMap,m.specularColorMapTransform)),d.specularIntensityMap&&(m.specularIntensityMap.value=d.specularIntensityMap,e(d.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,d){d.matcap&&(m.matcap.value=d.matcap)}function _(m,d){const w=t.get(d).light;m.referencePosition.value.setFromMatrixPosition(w.matrixWorld),m.nearDistance.value=w.shadow.camera.near,m.farDistance.value=w.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:s}}function I0(i,t,e,n){let s={},r={},a=[];const o=i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS);function c(w,T){const M=T.program;n.uniformBlockBinding(w,M)}function l(w,T){let M=s[w.id];M===void 0&&(g(w),M=h(w),s[w.id]=M,w.addEventListener("dispose",m));const F=T.program;n.updateUBOMapping(w,F);const P=t.render.frame;r[w.id]!==P&&(f(w),r[w.id]=P)}function h(w){const T=u();w.__bindingPointIndex=T;const M=i.createBuffer(),F=w.__size,P=w.usage;return i.bindBuffer(i.UNIFORM_BUFFER,M),i.bufferData(i.UNIFORM_BUFFER,F,P),i.bindBuffer(i.UNIFORM_BUFFER,null),i.bindBufferBase(i.UNIFORM_BUFFER,T,M),M}function u(){for(let w=0;w<o;w++)if(a.indexOf(w)===-1)return a.push(w),w;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function f(w){const T=s[w.id],M=w.uniforms,F=w.__cache;i.bindBuffer(i.UNIFORM_BUFFER,T);for(let P=0,N=M.length;P<N;P++){const D=Array.isArray(M[P])?M[P]:[M[P]];for(let y=0,S=D.length;y<S;y++){const U=D[y];if(p(U,P,y,F)===!0){const k=U.__offset,H=Array.isArray(U.value)?U.value:[U.value];let J=0;for(let Q=0;Q<H.length;Q++){const O=H[Q],tt=_(O);typeof O=="number"||typeof O=="boolean"?(U.__data[0]=O,i.bufferSubData(i.UNIFORM_BUFFER,k+J,U.__data)):O.isMatrix3?(U.__data[0]=O.elements[0],U.__data[1]=O.elements[1],U.__data[2]=O.elements[2],U.__data[3]=0,U.__data[4]=O.elements[3],U.__data[5]=O.elements[4],U.__data[6]=O.elements[5],U.__data[7]=0,U.__data[8]=O.elements[6],U.__data[9]=O.elements[7],U.__data[10]=O.elements[8],U.__data[11]=0):(O.toArray(U.__data,J),J+=tt.storage/Float32Array.BYTES_PER_ELEMENT)}i.bufferSubData(i.UNIFORM_BUFFER,k,U.__data)}}}i.bindBuffer(i.UNIFORM_BUFFER,null)}function p(w,T,M,F){const P=w.value,N=T+"_"+M;if(F[N]===void 0)return typeof P=="number"||typeof P=="boolean"?F[N]=P:F[N]=P.clone(),!0;{const D=F[N];if(typeof P=="number"||typeof P=="boolean"){if(D!==P)return F[N]=P,!0}else if(D.equals(P)===!1)return D.copy(P),!0}return!1}function g(w){const T=w.uniforms;let M=0;const F=16;for(let N=0,D=T.length;N<D;N++){const y=Array.isArray(T[N])?T[N]:[T[N]];for(let S=0,U=y.length;S<U;S++){const k=y[S],H=Array.isArray(k.value)?k.value:[k.value];for(let J=0,Q=H.length;J<Q;J++){const O=H[J],tt=_(O),W=M%F,ct=W%tt.boundary,ft=W+ct;M+=ct,ft!==0&&F-ft<tt.storage&&(M+=F-ft),k.__data=new Float32Array(tt.storage/Float32Array.BYTES_PER_ELEMENT),k.__offset=M,M+=tt.storage}}}const P=M%F;return P>0&&(M+=F-P),w.__size=M,w.__cache={},this}function _(w){const T={boundary:0,storage:0};return typeof w=="number"||typeof w=="boolean"?(T.boundary=4,T.storage=4):w.isVector2?(T.boundary=8,T.storage=8):w.isVector3||w.isColor?(T.boundary=16,T.storage=12):w.isVector4?(T.boundary=16,T.storage=16):w.isMatrix3?(T.boundary=48,T.storage=48):w.isMatrix4?(T.boundary=64,T.storage=64):w.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",w),T}function m(w){const T=w.target;T.removeEventListener("dispose",m);const M=a.indexOf(T.__bindingPointIndex);a.splice(M,1),i.deleteBuffer(s[T.id]),delete s[T.id],delete r[T.id]}function d(){for(const w in s)i.deleteBuffer(s[w]);a=[],s={},r={}}return{bind:c,update:l,dispose:d}}class U0{constructor(t={}){const{canvas:e=bf(),context:n=null,depth:s=!0,stencil:r=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:c=!0,preserveDrawingBuffer:l=!1,powerPreference:h="default",failIfMajorPerformanceCaveat:u=!1,reverseDepthBuffer:f=!1}=t;this.isWebGLRenderer=!0;let p;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");p=n.getContextAttributes().alpha}else p=a;const g=new Uint32Array(4),_=new Int32Array(4);let m=null,d=null;const w=[],T=[];this.domElement=e,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this._outputColorSpace=Le,this.toneMapping=Ti,this.toneMappingExposure=1;const M=this;let F=!1,P=0,N=0,D=null,y=-1,S=null;const U=new xe,k=new xe;let H=null;const J=new Kt(0);let Q=0,O=e.width,tt=e.height,W=1,ct=null,ft=null;const pt=new xe(0,0,O,tt),Rt=new xe(0,0,O,tt);let wt=!1;const X=new Wc;let K=!1,nt=!1;const it=new jt,vt=new jt,zt=new L,Zt=new xe,Ce={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};let ue=!1;function De(){return D===null?W:1}let G=n;function on(C,V){return e.getContext(C,V)}try{const C={alpha:!0,depth:s,stencil:r,antialias:o,premultipliedAlpha:c,preserveDrawingBuffer:l,powerPreference:h,failIfMajorPerformanceCaveat:u};if("setAttribute"in e&&e.setAttribute("data-engine",`three.js r${Uc}`),e.addEventListener("webglcontextlost",at,!1),e.addEventListener("webglcontextrestored",Et,!1),e.addEventListener("webglcontextcreationerror",St,!1),G===null){const V="webgl2";if(G=on(V,C),G===null)throw on(V)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(C){throw console.error("THREE.WebGLRenderer: "+C.message),C}let ae,ce,Wt,Ae,Ht,I,b,q,ot,lt,rt,Ft,Mt,Ct,de,dt,Pt,Xt,Yt,Lt,he,ee,ye,z;function xt(){ae=new zg(G),ae.init(),ee=new w0(G,ae),ce=new Ig(G,ae,t,ee),Wt=new S0(G,ae),ce.reverseDepthBuffer&&f&&Wt.buffers.depth.setReversed(!0),Ae=new Gg(G),Ht=new a0,I=new E0(G,ae,Wt,Ht,ce,ee,Ae),b=new Fg(M),q=new Bg(M),ot=new Kf(G),ye=new Ng(G,ot),lt=new Vg(G,ot,Ae,ye),rt=new Xg(G,lt,ot,Ae),Yt=new Wg(G,ce,I),dt=new Ug(Ht),Ft=new o0(M,b,q,ae,ce,ye,dt),Mt=new D0(M,Ht),Ct=new l0,de=new m0(ae),Xt=new Lg(M,b,q,Wt,rt,p,c),Pt=new y0(M,rt,ce),z=new I0(G,Ae,ce,Wt),Lt=new Dg(G,ae,Ae),he=new Hg(G,ae,Ae),Ae.programs=Ft.programs,M.capabilities=ce,M.extensions=ae,M.properties=Ht,M.renderLists=Ct,M.shadowMap=Pt,M.state=Wt,M.info=Ae}xt();const Z=new L0(M,G);this.xr=Z,this.getContext=function(){return G},this.getContextAttributes=function(){return G.getContextAttributes()},this.forceContextLoss=function(){const C=ae.get("WEBGL_lose_context");C&&C.loseContext()},this.forceContextRestore=function(){const C=ae.get("WEBGL_lose_context");C&&C.restoreContext()},this.getPixelRatio=function(){return W},this.setPixelRatio=function(C){C!==void 0&&(W=C,this.setSize(O,tt,!1))},this.getSize=function(C){return C.set(O,tt)},this.setSize=function(C,V,j=!0){if(Z.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}O=C,tt=V,e.width=Math.floor(C*W),e.height=Math.floor(V*W),j===!0&&(e.style.width=C+"px",e.style.height=V+"px"),this.setViewport(0,0,C,V)},this.getDrawingBufferSize=function(C){return C.set(O*W,tt*W).floor()},this.setDrawingBufferSize=function(C,V,j){O=C,tt=V,W=j,e.width=Math.floor(C*j),e.height=Math.floor(V*j),this.setViewport(0,0,C,V)},this.getCurrentViewport=function(C){return C.copy(U)},this.getViewport=function(C){return C.copy(pt)},this.setViewport=function(C,V,j,Y){C.isVector4?pt.set(C.x,C.y,C.z,C.w):pt.set(C,V,j,Y),Wt.viewport(U.copy(pt).multiplyScalar(W).round())},this.getScissor=function(C){return C.copy(Rt)},this.setScissor=function(C,V,j,Y){C.isVector4?Rt.set(C.x,C.y,C.z,C.w):Rt.set(C,V,j,Y),Wt.scissor(k.copy(Rt).multiplyScalar(W).round())},this.getScissorTest=function(){return wt},this.setScissorTest=function(C){Wt.setScissorTest(wt=C)},this.setOpaqueSort=function(C){ct=C},this.setTransparentSort=function(C){ft=C},this.getClearColor=function(C){return C.copy(Xt.getClearColor())},this.setClearColor=function(){Xt.setClearColor.apply(Xt,arguments)},this.getClearAlpha=function(){return Xt.getClearAlpha()},this.setClearAlpha=function(){Xt.setClearAlpha.apply(Xt,arguments)},this.clear=function(C=!0,V=!0,j=!0){let Y=0;if(C){let B=!1;if(D!==null){const ut=D.texture.format;B=ut===Vc||ut===zc||ut===Bc}if(B){const ut=D.texture.type,yt=ut===ci||ut===Xi||ut===cr||ut===Cs||ut===Oc||ut===kc,Dt=Xt.getClearColor(),It=Xt.getClearAlpha(),$t=Dt.r,te=Dt.g,Ut=Dt.b;yt?(g[0]=$t,g[1]=te,g[2]=Ut,g[3]=It,G.clearBufferuiv(G.COLOR,0,g)):(_[0]=$t,_[1]=te,_[2]=Ut,_[3]=It,G.clearBufferiv(G.COLOR,0,_))}else Y|=G.COLOR_BUFFER_BIT}V&&(Y|=G.DEPTH_BUFFER_BIT),j&&(Y|=G.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),G.clear(Y)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){e.removeEventListener("webglcontextlost",at,!1),e.removeEventListener("webglcontextrestored",Et,!1),e.removeEventListener("webglcontextcreationerror",St,!1),Ct.dispose(),de.dispose(),Ht.dispose(),b.dispose(),q.dispose(),rt.dispose(),ye.dispose(),z.dispose(),Ft.dispose(),Z.dispose(),Z.removeEventListener("sessionstart",Sr),Z.removeEventListener("sessionend",br),Yn.stop()};function at(C){C.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),F=!0}function Et(){console.log("THREE.WebGLRenderer: Context Restored."),F=!1;const C=Ae.autoReset,V=Pt.enabled,j=Pt.autoUpdate,Y=Pt.needsUpdate,B=Pt.type;xt(),Ae.autoReset=C,Pt.enabled=V,Pt.autoUpdate=j,Pt.needsUpdate=Y,Pt.type=B}function St(C){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",C.statusMessage)}function Qt(C){const V=C.target;V.removeEventListener("dispose",Qt),Re(V)}function Re(C){We(C),Ht.remove(C)}function We(C){const V=Ht.get(C).programs;V!==void 0&&(V.forEach(function(j){Ft.releaseProgram(j)}),C.isShaderMaterial&&Ft.releaseShaderCache(C))}this.renderBufferDirect=function(C,V,j,Y,B,ut){V===null&&(V=Ce);const yt=B.isMesh&&B.matrixWorld.determinant()<0,Dt=Yo(C,V,j,Y,B);Wt.setMaterial(Y,yt);let It=j.index,$t=1;if(Y.wireframe===!0){if(It=lt.getWireframeAttribute(j),It===void 0)return;$t=2}const te=j.drawRange,Ut=j.attributes.position;let fe=te.start*$t,Me=(te.start+te.count)*$t;ut!==null&&(fe=Math.max(fe,ut.start*$t),Me=Math.min(Me,(ut.start+ut.count)*$t)),It!==null?(fe=Math.max(fe,0),Me=Math.min(Me,It.count)):Ut!=null&&(fe=Math.max(fe,0),Me=Math.min(Me,Ut.count));const be=Me-fe;if(be<0||be===1/0)return;ye.setup(B,Y,Dt,j,It);let Oe,ge=Lt;if(It!==null&&(Oe=ot.get(It),ge=he,ge.setIndex(Oe)),B.isMesh)Y.wireframe===!0?(Wt.setLineWidth(Y.wireframeLinewidth*De()),ge.setMode(G.LINES)):ge.setMode(G.TRIANGLES);else if(B.isLine){let Ot=Y.linewidth;Ot===void 0&&(Ot=1),Wt.setLineWidth(Ot*De()),B.isLineSegments?ge.setMode(G.LINES):B.isLineLoop?ge.setMode(G.LINE_LOOP):ge.setMode(G.LINE_STRIP)}else B.isPoints?ge.setMode(G.POINTS):B.isSprite&&ge.setMode(G.TRIANGLES);if(B.isBatchedMesh)if(B._multiDrawInstances!==null)ge.renderMultiDrawInstances(B._multiDrawStarts,B._multiDrawCounts,B._multiDrawCount,B._multiDrawInstances);else if(ae.get("WEBGL_multi_draw"))ge.renderMultiDraw(B._multiDrawStarts,B._multiDrawCounts,B._multiDrawCount);else{const Ot=B._multiDrawStarts,Ln=B._multiDrawCounts,pe=B._multiDrawCount,pn=It?ot.get(It).bytesPerElement:1,pi=Ht.get(Y).currentProgram.getUniforms();for(let Ze=0;Ze<pe;Ze++)pi.setValue(G,"_gl_DrawID",Ze),ge.render(Ot[Ze]/pn,Ln[Ze])}else if(B.isInstancedMesh)ge.renderInstances(fe,be,B.count);else if(j.isInstancedBufferGeometry){const Ot=j._maxInstanceCount!==void 0?j._maxInstanceCount:1/0,Ln=Math.min(j.instanceCount,Ot);ge.renderInstances(fe,be,Ln)}else ge.render(fe,be)};function ie(C,V,j){C.transparent===!0&&C.side===un&&C.forceSinglePass===!1?(C.side=dn,C.needsUpdate=!0,Ji(C,V,j),C.side=ai,C.needsUpdate=!0,Ji(C,V,j),C.side=un):Ji(C,V,j)}this.compile=function(C,V,j=null){j===null&&(j=C),d=de.get(j),d.init(V),T.push(d),j.traverseVisible(function(B){B.isLight&&B.layers.test(V.layers)&&(d.pushLight(B),B.castShadow&&d.pushShadow(B))}),C!==j&&C.traverseVisible(function(B){B.isLight&&B.layers.test(V.layers)&&(d.pushLight(B),B.castShadow&&d.pushShadow(B))}),d.setupLights();const Y=new Set;return C.traverse(function(B){if(!(B.isMesh||B.isPoints||B.isLine||B.isSprite))return;const ut=B.material;if(ut)if(Array.isArray(ut))for(let yt=0;yt<ut.length;yt++){const Dt=ut[yt];ie(Dt,j,B),Y.add(Dt)}else ie(ut,j,B),Y.add(ut)}),T.pop(),d=null,Y},this.compileAsync=function(C,V,j=null){const Y=this.compile(C,V,j);return new Promise(B=>{function ut(){if(Y.forEach(function(yt){Ht.get(yt).currentProgram.isReady()&&Y.delete(yt)}),Y.size===0){B(C);return}setTimeout(ut,10)}ae.get("KHR_parallel_shader_compile")!==null?ut():setTimeout(ut,10)})};let an=null;function Pn(C){an&&an(C)}function Sr(){Yn.stop()}function br(){Yn.start()}const Yn=new vu;Yn.setAnimationLoop(Pn),typeof self<"u"&&Yn.setContext(self),this.setAnimationLoop=function(C){an=C,Z.setAnimationLoop(C),C===null?Yn.stop():Yn.start()},Z.addEventListener("sessionstart",Sr),Z.addEventListener("sessionend",br),this.render=function(C,V){if(V!==void 0&&V.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(F===!0)return;if(C.matrixWorldAutoUpdate===!0&&C.updateMatrixWorld(),V.parent===null&&V.matrixWorldAutoUpdate===!0&&V.updateMatrixWorld(),Z.enabled===!0&&Z.isPresenting===!0&&(Z.cameraAutoUpdate===!0&&Z.updateCamera(V),V=Z.getCamera()),C.isScene===!0&&C.onBeforeRender(M,C,V,D),d=de.get(C,T.length),d.init(V),T.push(d),vt.multiplyMatrices(V.projectionMatrix,V.matrixWorldInverse),X.setFromProjectionMatrix(vt),nt=this.localClippingEnabled,K=dt.init(this.clippingPlanes,nt),m=Ct.get(C,w.length),m.init(),w.push(m),Z.enabled===!0&&Z.isPresenting===!0){const ut=M.xr.getDepthSensingMesh();ut!==null&&Gs(ut,V,-1/0,M.sortObjects)}Gs(C,V,0,M.sortObjects),m.finish(),M.sortObjects===!0&&m.sort(ct,ft),ue=Z.enabled===!1||Z.isPresenting===!1||Z.hasDepthSensing()===!1,ue&&Xt.addToRenderList(m,C),this.info.render.frame++,K===!0&&dt.beginShadows();const j=d.state.shadowsArray;Pt.render(j,C,V),K===!0&&dt.endShadows(),this.info.autoReset===!0&&this.info.reset();const Y=m.opaque,B=m.transmissive;if(d.setupLights(),V.isArrayCamera){const ut=V.cameras;if(B.length>0)for(let yt=0,Dt=ut.length;yt<Dt;yt++){const It=ut[yt];Ws(Y,B,C,It)}ue&&Xt.render(C);for(let yt=0,Dt=ut.length;yt<Dt;yt++){const It=ut[yt];Er(m,C,It,It.viewport)}}else B.length>0&&Ws(Y,B,C,V),ue&&Xt.render(C),Er(m,C,V);D!==null&&(I.updateMultisampleRenderTarget(D),I.updateRenderTargetMipmap(D)),C.isScene===!0&&C.onAfterRender(M,C,V),ye.resetDefaultState(),y=-1,S=null,T.pop(),T.length>0?(d=T[T.length-1],K===!0&&dt.setGlobalState(M.clippingPlanes,d.state.camera)):d=null,w.pop(),w.length>0?m=w[w.length-1]:m=null};function Gs(C,V,j,Y){if(C.visible===!1)return;if(C.layers.test(V.layers)){if(C.isGroup)j=C.renderOrder;else if(C.isLOD)C.autoUpdate===!0&&C.update(V);else if(C.isLight)d.pushLight(C),C.castShadow&&d.pushShadow(C);else if(C.isSprite){if(!C.frustumCulled||X.intersectsSprite(C)){Y&&Zt.setFromMatrixPosition(C.matrixWorld).applyMatrix4(vt);const yt=rt.update(C),Dt=C.material;Dt.visible&&m.push(C,yt,Dt,j,Zt.z,null)}}else if((C.isMesh||C.isLine||C.isPoints)&&(!C.frustumCulled||X.intersectsObject(C))){const yt=rt.update(C),Dt=C.material;if(Y&&(C.boundingSphere!==void 0?(C.boundingSphere===null&&C.computeBoundingSphere(),Zt.copy(C.boundingSphere.center)):(yt.boundingSphere===null&&yt.computeBoundingSphere(),Zt.copy(yt.boundingSphere.center)),Zt.applyMatrix4(C.matrixWorld).applyMatrix4(vt)),Array.isArray(Dt)){const It=yt.groups;for(let $t=0,te=It.length;$t<te;$t++){const Ut=It[$t],fe=Dt[Ut.materialIndex];fe&&fe.visible&&m.push(C,yt,fe,j,Zt.z,Ut)}}else Dt.visible&&m.push(C,yt,Dt,j,Zt.z,null)}}const ut=C.children;for(let yt=0,Dt=ut.length;yt<Dt;yt++)Gs(ut[yt],V,j,Y)}function Er(C,V,j,Y){const B=C.opaque,ut=C.transmissive,yt=C.transparent;d.setupLightsView(j),K===!0&&dt.setGlobalState(M.clippingPlanes,j),Y&&Wt.viewport(U.copy(Y)),B.length>0&&Ki(B,V,j),ut.length>0&&Ki(ut,V,j),yt.length>0&&Ki(yt,V,j),Wt.buffers.depth.setTest(!0),Wt.buffers.depth.setMask(!0),Wt.buffers.color.setMask(!0),Wt.setPolygonOffset(!1)}function Ws(C,V,j,Y){if((j.isScene===!0?j.overrideMaterial:null)!==null)return;d.state.transmissionRenderTarget[Y.id]===void 0&&(d.state.transmissionRenderTarget[Y.id]=new qi(1,1,{generateMipmaps:!0,type:ae.has("EXT_color_buffer_half_float")||ae.has("EXT_color_buffer_float")?gr:ci,minFilter:si,samples:4,stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:le.workingColorSpace}));const ut=d.state.transmissionRenderTarget[Y.id],yt=Y.viewport||U;ut.setSize(yt.z,yt.w);const Dt=M.getRenderTarget();M.setRenderTarget(ut),M.getClearColor(J),Q=M.getClearAlpha(),Q<1&&M.setClearColor(16777215,.5),M.clear(),ue&&Xt.render(j);const It=M.toneMapping;M.toneMapping=Ti;const $t=Y.viewport;if(Y.viewport!==void 0&&(Y.viewport=void 0),d.setupLightsView(Y),K===!0&&dt.setGlobalState(M.clippingPlanes,Y),Ki(C,j,Y),I.updateMultisampleRenderTarget(ut),I.updateRenderTargetMipmap(ut),ae.has("WEBGL_multisampled_render_to_texture")===!1){let te=!1;for(let Ut=0,fe=V.length;Ut<fe;Ut++){const Me=V[Ut],be=Me.object,Oe=Me.geometry,ge=Me.material,Ot=Me.group;if(ge.side===un&&be.layers.test(Y.layers)){const Ln=ge.side;ge.side=dn,ge.needsUpdate=!0,Xs(be,j,Y,Oe,ge,Ot),ge.side=Ln,ge.needsUpdate=!0,te=!0}}te===!0&&(I.updateMultisampleRenderTarget(ut),I.updateRenderTargetMipmap(ut))}M.setRenderTarget(Dt),M.setClearColor(J,Q),$t!==void 0&&(Y.viewport=$t),M.toneMapping=It}function Ki(C,V,j){const Y=V.isScene===!0?V.overrideMaterial:null;for(let B=0,ut=C.length;B<ut;B++){const yt=C[B],Dt=yt.object,It=yt.geometry,$t=Y===null?yt.material:Y,te=yt.group;Dt.layers.test(j.layers)&&Xs(Dt,V,j,It,$t,te)}}function Xs(C,V,j,Y,B,ut){C.onBeforeRender(M,V,j,Y,B,ut),C.modelViewMatrix.multiplyMatrices(j.matrixWorldInverse,C.matrixWorld),C.normalMatrix.getNormalMatrix(C.modelViewMatrix),B.onBeforeRender(M,V,j,Y,C,ut),B.transparent===!0&&B.side===un&&B.forceSinglePass===!1?(B.side=dn,B.needsUpdate=!0,M.renderBufferDirect(j,V,Y,B,C,ut),B.side=ai,B.needsUpdate=!0,M.renderBufferDirect(j,V,Y,B,C,ut),B.side=un):M.renderBufferDirect(j,V,Y,B,C,ut),C.onAfterRender(M,V,j,Y,B,ut)}function Ji(C,V,j){V.isScene!==!0&&(V=Ce);const Y=Ht.get(C),B=d.state.lights,ut=d.state.shadowsArray,yt=B.state.version,Dt=Ft.getParameters(C,B.state,ut,V,j),It=Ft.getProgramCacheKey(Dt);let $t=Y.programs;Y.environment=C.isMeshStandardMaterial?V.environment:null,Y.fog=V.fog,Y.envMap=(C.isMeshStandardMaterial?q:b).get(C.envMap||Y.environment),Y.envMapRotation=Y.environment!==null&&C.envMap===null?V.environmentRotation:C.envMapRotation,$t===void 0&&(C.addEventListener("dispose",Qt),$t=new Map,Y.programs=$t);let te=$t.get(It);if(te!==void 0){if(Y.currentProgram===te&&Y.lightsStateVersion===yt)return Tr(C,Dt),te}else Dt.uniforms=Ft.getUniforms(C),C.onBeforeCompile(Dt,M),te=Ft.acquireProgram(Dt,It),$t.set(It,te),Y.uniforms=Dt.uniforms;const Ut=Y.uniforms;return(!C.isShaderMaterial&&!C.isRawShaderMaterial||C.clipping===!0)&&(Ut.clippingPlanes=dt.uniform),Tr(C,Dt),Y.needsLights=Ko(C),Y.lightsStateVersion=yt,Y.needsLights&&(Ut.ambientLightColor.value=B.state.ambient,Ut.lightProbe.value=B.state.probe,Ut.directionalLights.value=B.state.directional,Ut.directionalLightShadows.value=B.state.directionalShadow,Ut.spotLights.value=B.state.spot,Ut.spotLightShadows.value=B.state.spotShadow,Ut.rectAreaLights.value=B.state.rectArea,Ut.ltc_1.value=B.state.rectAreaLTC1,Ut.ltc_2.value=B.state.rectAreaLTC2,Ut.pointLights.value=B.state.point,Ut.pointLightShadows.value=B.state.pointShadow,Ut.hemisphereLights.value=B.state.hemi,Ut.directionalShadowMap.value=B.state.directionalShadowMap,Ut.directionalShadowMatrix.value=B.state.directionalShadowMatrix,Ut.spotShadowMap.value=B.state.spotShadowMap,Ut.spotLightMatrix.value=B.state.spotLightMatrix,Ut.spotLightMap.value=B.state.spotLightMap,Ut.pointShadowMap.value=B.state.pointShadowMap,Ut.pointShadowMatrix.value=B.state.pointShadowMatrix),Y.currentProgram=te,Y.uniformsList=null,te}function wr(C){if(C.uniformsList===null){const V=C.currentProgram.getUniforms();C.uniformsList=go.seqWithValue(V.seq,C.uniforms)}return C.uniformsList}function Tr(C,V){const j=Ht.get(C);j.outputColorSpace=V.outputColorSpace,j.batching=V.batching,j.batchingColor=V.batchingColor,j.instancing=V.instancing,j.instancingColor=V.instancingColor,j.instancingMorph=V.instancingMorph,j.skinning=V.skinning,j.morphTargets=V.morphTargets,j.morphNormals=V.morphNormals,j.morphColors=V.morphColors,j.morphTargetsCount=V.morphTargetsCount,j.numClippingPlanes=V.numClippingPlanes,j.numIntersection=V.numClipIntersection,j.vertexAlphas=V.vertexAlphas,j.vertexTangents=V.vertexTangents,j.toneMapping=V.toneMapping}function Yo(C,V,j,Y,B){V.isScene!==!0&&(V=Ce),I.resetTextureUnits();const ut=V.fog,yt=Y.isMeshStandardMaterial?V.environment:null,Dt=D===null?M.outputColorSpace:D.isXRRenderTarget===!0?D.texture.colorSpace:Us,It=(Y.isMeshStandardMaterial?q:b).get(Y.envMap||yt),$t=Y.vertexColors===!0&&!!j.attributes.color&&j.attributes.color.itemSize===4,te=!!j.attributes.tangent&&(!!Y.normalMap||Y.anisotropy>0),Ut=!!j.morphAttributes.position,fe=!!j.morphAttributes.normal,Me=!!j.morphAttributes.color;let be=Ti;Y.toneMapped&&(D===null||D.isXRRenderTarget===!0)&&(be=M.toneMapping);const Oe=j.morphAttributes.position||j.morphAttributes.normal||j.morphAttributes.color,ge=Oe!==void 0?Oe.length:0,Ot=Ht.get(Y),Ln=d.state.lights;if(K===!0&&(nt===!0||C!==S)){const Qe=C===S&&Y.id===y;dt.setState(Y,C,Qe)}let pe=!1;Y.version===Ot.__version?(Ot.needsLights&&Ot.lightsStateVersion!==Ln.state.version||Ot.outputColorSpace!==Dt||B.isBatchedMesh&&Ot.batching===!1||!B.isBatchedMesh&&Ot.batching===!0||B.isBatchedMesh&&Ot.batchingColor===!0&&B.colorTexture===null||B.isBatchedMesh&&Ot.batchingColor===!1&&B.colorTexture!==null||B.isInstancedMesh&&Ot.instancing===!1||!B.isInstancedMesh&&Ot.instancing===!0||B.isSkinnedMesh&&Ot.skinning===!1||!B.isSkinnedMesh&&Ot.skinning===!0||B.isInstancedMesh&&Ot.instancingColor===!0&&B.instanceColor===null||B.isInstancedMesh&&Ot.instancingColor===!1&&B.instanceColor!==null||B.isInstancedMesh&&Ot.instancingMorph===!0&&B.morphTexture===null||B.isInstancedMesh&&Ot.instancingMorph===!1&&B.morphTexture!==null||Ot.envMap!==It||Y.fog===!0&&Ot.fog!==ut||Ot.numClippingPlanes!==void 0&&(Ot.numClippingPlanes!==dt.numPlanes||Ot.numIntersection!==dt.numIntersection)||Ot.vertexAlphas!==$t||Ot.vertexTangents!==te||Ot.morphTargets!==Ut||Ot.morphNormals!==fe||Ot.morphColors!==Me||Ot.toneMapping!==be||Ot.morphTargetsCount!==ge)&&(pe=!0):(pe=!0,Ot.__version=Y.version);let pn=Ot.currentProgram;pe===!0&&(pn=Ji(Y,V,B));let pi=!1,Ze=!1,mi=!1;const Jt=pn.getUniforms(),cn=Ot.uniforms;if(Wt.useProgram(pn.program)&&(pi=!0,Ze=!0,mi=!0),Y.id!==y&&(y=Y.id,Ze=!0),pi||S!==C){Wt.buffers.depth.getReversed()?(it.copy(C.projectionMatrix),wf(it),Tf(it),Jt.setValue(G,"projectionMatrix",it)):Jt.setValue(G,"projectionMatrix",C.projectionMatrix),Jt.setValue(G,"viewMatrix",C.matrixWorldInverse);const Nn=Jt.map.cameraPosition;Nn!==void 0&&Nn.setValue(G,zt.setFromMatrixPosition(C.matrixWorld)),ce.logarithmicDepthBuffer&&Jt.setValue(G,"logDepthBufFC",2/(Math.log(C.far+1)/Math.LN2)),(Y.isMeshPhongMaterial||Y.isMeshToonMaterial||Y.isMeshLambertMaterial||Y.isMeshBasicMaterial||Y.isMeshStandardMaterial||Y.isShaderMaterial)&&Jt.setValue(G,"isOrthographic",C.isOrthographicCamera===!0),S!==C&&(S=C,Ze=!0,mi=!0)}if(B.isSkinnedMesh){Jt.setOptional(G,B,"bindMatrix"),Jt.setOptional(G,B,"bindMatrixInverse");const Qe=B.skeleton;Qe&&(Qe.boneTexture===null&&Qe.computeBoneTexture(),Jt.setValue(G,"boneTexture",Qe.boneTexture,I))}B.isBatchedMesh&&(Jt.setOptional(G,B,"batchingTexture"),Jt.setValue(G,"batchingTexture",B._matricesTexture,I),Jt.setOptional(G,B,"batchingIdTexture"),Jt.setValue(G,"batchingIdTexture",B._indirectTexture,I),Jt.setOptional(G,B,"batchingColorTexture"),B._colorsTexture!==null&&Jt.setValue(G,"batchingColorTexture",B._colorsTexture,I));const Ni=j.morphAttributes;if((Ni.position!==void 0||Ni.normal!==void 0||Ni.color!==void 0)&&Yt.update(B,j,pn),(Ze||Ot.receiveShadow!==B.receiveShadow)&&(Ot.receiveShadow=B.receiveShadow,Jt.setValue(G,"receiveShadow",B.receiveShadow)),Y.isMeshGouraudMaterial&&Y.envMap!==null&&(cn.envMap.value=It,cn.flipEnvMap.value=It.isCubeTexture&&It.isRenderTargetTexture===!1?-1:1),Y.isMeshStandardMaterial&&Y.envMap===null&&V.environment!==null&&(cn.envMapIntensity.value=V.environmentIntensity),Ze&&(Jt.setValue(G,"toneMappingExposure",M.toneMappingExposure),Ot.needsLights&&$o(cn,mi),ut&&Y.fog===!0&&Mt.refreshFogUniforms(cn,ut),Mt.refreshMaterialUniforms(cn,Y,W,tt,d.state.transmissionRenderTarget[C.id]),go.upload(G,wr(Ot),cn,I)),Y.isShaderMaterial&&Y.uniformsNeedUpdate===!0&&(go.upload(G,wr(Ot),cn,I),Y.uniformsNeedUpdate=!1),Y.isSpriteMaterial&&Jt.setValue(G,"center",B.center),Jt.setValue(G,"modelViewMatrix",B.modelViewMatrix),Jt.setValue(G,"normalMatrix",B.normalMatrix),Jt.setValue(G,"modelMatrix",B.matrixWorld),Y.isShaderMaterial||Y.isRawShaderMaterial){const Qe=Y.uniformsGroups;for(let Nn=0,Sn=Qe.length;Nn<Sn;Nn++){const Di=Qe[Nn];z.update(Di,pn),z.bind(Di,pn)}}return pn}function $o(C,V){C.ambientLightColor.needsUpdate=V,C.lightProbe.needsUpdate=V,C.directionalLights.needsUpdate=V,C.directionalLightShadows.needsUpdate=V,C.pointLights.needsUpdate=V,C.pointLightShadows.needsUpdate=V,C.spotLights.needsUpdate=V,C.spotLightShadows.needsUpdate=V,C.rectAreaLights.needsUpdate=V,C.hemisphereLights.needsUpdate=V}function Ko(C){return C.isMeshLambertMaterial||C.isMeshToonMaterial||C.isMeshPhongMaterial||C.isMeshStandardMaterial||C.isShadowMaterial||C.isShaderMaterial&&C.lights===!0}this.getActiveCubeFace=function(){return P},this.getActiveMipmapLevel=function(){return N},this.getRenderTarget=function(){return D},this.setRenderTargetTextures=function(C,V,j){Ht.get(C.texture).__webglTexture=V,Ht.get(C.depthTexture).__webglTexture=j;const Y=Ht.get(C);Y.__hasExternalTextures=!0,Y.__autoAllocateDepthBuffer=j===void 0,Y.__autoAllocateDepthBuffer||ae.has("WEBGL_multisampled_render_to_texture")===!0&&(console.warn("THREE.WebGLRenderer: Render-to-texture extension was disabled because an external texture was provided"),Y.__useRenderToTexture=!1)},this.setRenderTargetFramebuffer=function(C,V){const j=Ht.get(C);j.__webglFramebuffer=V,j.__useDefaultFramebuffer=V===void 0},this.setRenderTarget=function(C,V=0,j=0){D=C,P=V,N=j;let Y=!0,B=null,ut=!1,yt=!1;if(C){const It=Ht.get(C);if(It.__useDefaultFramebuffer!==void 0)Wt.bindFramebuffer(G.FRAMEBUFFER,null),Y=!1;else if(It.__webglFramebuffer===void 0)I.setupRenderTarget(C);else if(It.__hasExternalTextures)I.rebindTextures(C,Ht.get(C.texture).__webglTexture,Ht.get(C.depthTexture).__webglTexture);else if(C.depthBuffer){const Ut=C.depthTexture;if(It.__boundDepthTexture!==Ut){if(Ut!==null&&Ht.has(Ut)&&(C.width!==Ut.image.width||C.height!==Ut.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");I.setupDepthRenderbuffer(C)}}const $t=C.texture;($t.isData3DTexture||$t.isDataArrayTexture||$t.isCompressedArrayTexture)&&(yt=!0);const te=Ht.get(C).__webglFramebuffer;C.isWebGLCubeRenderTarget?(Array.isArray(te[V])?B=te[V][j]:B=te[V],ut=!0):C.samples>0&&I.useMultisampledRTT(C)===!1?B=Ht.get(C).__webglMultisampledFramebuffer:Array.isArray(te)?B=te[j]:B=te,U.copy(C.viewport),k.copy(C.scissor),H=C.scissorTest}else U.copy(pt).multiplyScalar(W).floor(),k.copy(Rt).multiplyScalar(W).floor(),H=wt;if(Wt.bindFramebuffer(G.FRAMEBUFFER,B)&&Y&&Wt.drawBuffers(C,B),Wt.viewport(U),Wt.scissor(k),Wt.setScissorTest(H),ut){const It=Ht.get(C.texture);G.framebufferTexture2D(G.FRAMEBUFFER,G.COLOR_ATTACHMENT0,G.TEXTURE_CUBE_MAP_POSITIVE_X+V,It.__webglTexture,j)}else if(yt){const It=Ht.get(C.texture),$t=V||0;G.framebufferTextureLayer(G.FRAMEBUFFER,G.COLOR_ATTACHMENT0,It.__webglTexture,j||0,$t)}y=-1},this.readRenderTargetPixels=function(C,V,j,Y,B,ut,yt){if(!(C&&C.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Dt=Ht.get(C).__webglFramebuffer;if(C.isWebGLCubeRenderTarget&&yt!==void 0&&(Dt=Dt[yt]),Dt){Wt.bindFramebuffer(G.FRAMEBUFFER,Dt);try{const It=C.texture,$t=It.format,te=It.type;if(!ce.textureFormatReadable($t)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!ce.textureTypeReadable(te)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}V>=0&&V<=C.width-Y&&j>=0&&j<=C.height-B&&G.readPixels(V,j,Y,B,ee.convert($t),ee.convert(te),ut)}finally{const It=D!==null?Ht.get(D).__webglFramebuffer:null;Wt.bindFramebuffer(G.FRAMEBUFFER,It)}}},this.readRenderTargetPixelsAsync=async function(C,V,j,Y,B,ut,yt){if(!(C&&C.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Dt=Ht.get(C).__webglFramebuffer;if(C.isWebGLCubeRenderTarget&&yt!==void 0&&(Dt=Dt[yt]),Dt){const It=C.texture,$t=It.format,te=It.type;if(!ce.textureFormatReadable($t))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!ce.textureTypeReadable(te))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");if(V>=0&&V<=C.width-Y&&j>=0&&j<=C.height-B){Wt.bindFramebuffer(G.FRAMEBUFFER,Dt);const Ut=G.createBuffer();G.bindBuffer(G.PIXEL_PACK_BUFFER,Ut),G.bufferData(G.PIXEL_PACK_BUFFER,ut.byteLength,G.STREAM_READ),G.readPixels(V,j,Y,B,ee.convert($t),ee.convert(te),0);const fe=D!==null?Ht.get(D).__webglFramebuffer:null;Wt.bindFramebuffer(G.FRAMEBUFFER,fe);const Me=G.fenceSync(G.SYNC_GPU_COMMANDS_COMPLETE,0);return G.flush(),await Ef(G,Me,4),G.bindBuffer(G.PIXEL_PACK_BUFFER,Ut),G.getBufferSubData(G.PIXEL_PACK_BUFFER,0,ut),G.deleteBuffer(Ut),G.deleteSync(Me),ut}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")}},this.copyFramebufferToTexture=function(C,V=null,j=0){C.isTexture!==!0&&(Zs("WebGLRenderer: copyFramebufferToTexture function signature has changed."),V=arguments[0]||null,C=arguments[1]);const Y=Math.pow(2,-j),B=Math.floor(C.image.width*Y),ut=Math.floor(C.image.height*Y),yt=V!==null?V.x:0,Dt=V!==null?V.y:0;I.setTexture2D(C,0),G.copyTexSubImage2D(G.TEXTURE_2D,j,0,0,yt,Dt,B,ut),Wt.unbindTexture()},this.copyTextureToTexture=function(C,V,j=null,Y=null,B=0){C.isTexture!==!0&&(Zs("WebGLRenderer: copyTextureToTexture function signature has changed."),Y=arguments[0]||null,C=arguments[1],V=arguments[2],B=arguments[3]||0,j=null);let ut,yt,Dt,It,$t,te,Ut,fe,Me;const be=C.isCompressedTexture?C.mipmaps[B]:C.image;j!==null?(ut=j.max.x-j.min.x,yt=j.max.y-j.min.y,Dt=j.isBox3?j.max.z-j.min.z:1,It=j.min.x,$t=j.min.y,te=j.isBox3?j.min.z:0):(ut=be.width,yt=be.height,Dt=be.depth||1,It=0,$t=0,te=0),Y!==null?(Ut=Y.x,fe=Y.y,Me=Y.z):(Ut=0,fe=0,Me=0);const Oe=ee.convert(V.format),ge=ee.convert(V.type);let Ot;V.isData3DTexture?(I.setTexture3D(V,0),Ot=G.TEXTURE_3D):V.isDataArrayTexture||V.isCompressedArrayTexture?(I.setTexture2DArray(V,0),Ot=G.TEXTURE_2D_ARRAY):(I.setTexture2D(V,0),Ot=G.TEXTURE_2D),G.pixelStorei(G.UNPACK_FLIP_Y_WEBGL,V.flipY),G.pixelStorei(G.UNPACK_PREMULTIPLY_ALPHA_WEBGL,V.premultiplyAlpha),G.pixelStorei(G.UNPACK_ALIGNMENT,V.unpackAlignment);const Ln=G.getParameter(G.UNPACK_ROW_LENGTH),pe=G.getParameter(G.UNPACK_IMAGE_HEIGHT),pn=G.getParameter(G.UNPACK_SKIP_PIXELS),pi=G.getParameter(G.UNPACK_SKIP_ROWS),Ze=G.getParameter(G.UNPACK_SKIP_IMAGES);G.pixelStorei(G.UNPACK_ROW_LENGTH,be.width),G.pixelStorei(G.UNPACK_IMAGE_HEIGHT,be.height),G.pixelStorei(G.UNPACK_SKIP_PIXELS,It),G.pixelStorei(G.UNPACK_SKIP_ROWS,$t),G.pixelStorei(G.UNPACK_SKIP_IMAGES,te);const mi=C.isDataArrayTexture||C.isData3DTexture,Jt=V.isDataArrayTexture||V.isData3DTexture;if(C.isRenderTargetTexture||C.isDepthTexture){const cn=Ht.get(C),Ni=Ht.get(V),Qe=Ht.get(cn.__renderTarget),Nn=Ht.get(Ni.__renderTarget);Wt.bindFramebuffer(G.READ_FRAMEBUFFER,Qe.__webglFramebuffer),Wt.bindFramebuffer(G.DRAW_FRAMEBUFFER,Nn.__webglFramebuffer);for(let Sn=0;Sn<Dt;Sn++)mi&&G.framebufferTextureLayer(G.READ_FRAMEBUFFER,G.COLOR_ATTACHMENT0,Ht.get(C).__webglTexture,B,te+Sn),C.isDepthTexture?(Jt&&G.framebufferTextureLayer(G.DRAW_FRAMEBUFFER,G.COLOR_ATTACHMENT0,Ht.get(V).__webglTexture,B,Me+Sn),G.blitFramebuffer(It,$t,ut,yt,Ut,fe,ut,yt,G.DEPTH_BUFFER_BIT,G.NEAREST)):Jt?G.copyTexSubImage3D(Ot,B,Ut,fe,Me+Sn,It,$t,ut,yt):G.copyTexSubImage2D(Ot,B,Ut,fe,Me+Sn,It,$t,ut,yt);Wt.bindFramebuffer(G.READ_FRAMEBUFFER,null),Wt.bindFramebuffer(G.DRAW_FRAMEBUFFER,null)}else Jt?C.isDataTexture||C.isData3DTexture?G.texSubImage3D(Ot,B,Ut,fe,Me,ut,yt,Dt,Oe,ge,be.data):V.isCompressedArrayTexture?G.compressedTexSubImage3D(Ot,B,Ut,fe,Me,ut,yt,Dt,Oe,be.data):G.texSubImage3D(Ot,B,Ut,fe,Me,ut,yt,Dt,Oe,ge,be):C.isDataTexture?G.texSubImage2D(G.TEXTURE_2D,B,Ut,fe,ut,yt,Oe,ge,be.data):C.isCompressedTexture?G.compressedTexSubImage2D(G.TEXTURE_2D,B,Ut,fe,be.width,be.height,Oe,be.data):G.texSubImage2D(G.TEXTURE_2D,B,Ut,fe,ut,yt,Oe,ge,be);G.pixelStorei(G.UNPACK_ROW_LENGTH,Ln),G.pixelStorei(G.UNPACK_IMAGE_HEIGHT,pe),G.pixelStorei(G.UNPACK_SKIP_PIXELS,pn),G.pixelStorei(G.UNPACK_SKIP_ROWS,pi),G.pixelStorei(G.UNPACK_SKIP_IMAGES,Ze),B===0&&V.generateMipmaps&&G.generateMipmap(Ot),Wt.unbindTexture()},this.copyTextureToTexture3D=function(C,V,j=null,Y=null,B=0){return C.isTexture!==!0&&(Zs("WebGLRenderer: copyTextureToTexture3D function signature has changed."),j=arguments[0]||null,Y=arguments[1]||null,C=arguments[2],V=arguments[3],B=arguments[4]||0),Zs('WebGLRenderer: copyTextureToTexture3D function has been deprecated. Use "copyTextureToTexture" instead.'),this.copyTextureToTexture(C,V,j,Y,B)},this.initRenderTarget=function(C){Ht.get(C).__webglFramebuffer===void 0&&I.setupRenderTarget(C)},this.initTexture=function(C){C.isCubeTexture?I.setTextureCube(C,0):C.isData3DTexture?I.setTexture3D(C,0):C.isDataArrayTexture||C.isCompressedArrayTexture?I.setTexture2DArray(C,0):I.setTexture2D(C,0),Wt.unbindTexture()},this.resetState=function(){P=0,N=0,D=null,Wt.reset(),ye.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return ri}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(t){this._outputColorSpace=t;const e=this.getContext();e.drawingBufferColorspace=le._getDrawingBufferColorSpace(t),e.unpackColorSpace=le._getUnpackColorSpace()}}class jc{constructor(t,e=1,n=1e3){this.isFog=!0,this.name="",this.color=new Kt(t),this.near=e,this.far=n}clone(){return new jc(this.color,this.near,this.far)}toJSON(){return{type:"Fog",name:this.name,color:this.color.getHex(),near:this.near,far:this.far}}}class Eu extends Ne{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new fn,this.environmentIntensity=1,this.environmentRotation=new fn,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(t,e){return super.copy(t,e),t.background!==null&&(this.background=t.background.clone()),t.environment!==null&&(this.environment=t.environment.clone()),t.fog!==null&&(this.fog=t.fog.clone()),this.backgroundBlurriness=t.backgroundBlurriness,this.backgroundIntensity=t.backgroundIntensity,this.backgroundRotation.copy(t.backgroundRotation),this.environmentIntensity=t.environmentIntensity,this.environmentRotation.copy(t.environmentRotation),t.overrideMaterial!==null&&(this.overrideMaterial=t.overrideMaterial.clone()),this.matrixAutoUpdate=t.matrixAutoUpdate,this}toJSON(t){const e=super.toJSON(t);return this.fog!==null&&(e.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(e.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(e.object.backgroundIntensity=this.backgroundIntensity),e.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(e.object.environmentIntensity=this.environmentIntensity),e.object.environmentRotation=this.environmentRotation.toArray(),e}}const hh=new L,uh=new xe,dh=new xe,F0=new L,fh=new jt,Kr=new L,Ta=new di,ph=new jt,Aa=new Fs;class O0 extends me{constructor(t,e){super(t,e),this.isSkinnedMesh=!0,this.type="SkinnedMesh",this.bindMode=ul,this.bindMatrix=new jt,this.bindMatrixInverse=new jt,this.boundingBox=null,this.boundingSphere=null}computeBoundingBox(){const t=this.geometry;this.boundingBox===null&&(this.boundingBox=new Xn),this.boundingBox.makeEmpty();const e=t.getAttribute("position");for(let n=0;n<e.count;n++)this.getVertexPosition(n,Kr),this.boundingBox.expandByPoint(Kr)}computeBoundingSphere(){const t=this.geometry;this.boundingSphere===null&&(this.boundingSphere=new di),this.boundingSphere.makeEmpty();const e=t.getAttribute("position");for(let n=0;n<e.count;n++)this.getVertexPosition(n,Kr),this.boundingSphere.expandByPoint(Kr)}copy(t,e){return super.copy(t,e),this.bindMode=t.bindMode,this.bindMatrix.copy(t.bindMatrix),this.bindMatrixInverse.copy(t.bindMatrixInverse),this.skeleton=t.skeleton,t.boundingBox!==null&&(this.boundingBox=t.boundingBox.clone()),t.boundingSphere!==null&&(this.boundingSphere=t.boundingSphere.clone()),this}raycast(t,e){const n=this.material,s=this.matrixWorld;n!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),Ta.copy(this.boundingSphere),Ta.applyMatrix4(s),t.ray.intersectsSphere(Ta)!==!1&&(ph.copy(s).invert(),Aa.copy(t.ray).applyMatrix4(ph),!(this.boundingBox!==null&&Aa.intersectsBox(this.boundingBox)===!1)&&this._computeIntersections(t,e,Aa)))}getVertexPosition(t,e){return super.getVertexPosition(t,e),this.applyBoneTransform(t,e),e}bind(t,e){this.skeleton=t,e===void 0&&(this.updateMatrixWorld(!0),this.skeleton.calculateInverses(),e=this.matrixWorld),this.bindMatrix.copy(e),this.bindMatrixInverse.copy(e).invert()}pose(){this.skeleton.pose()}normalizeSkinWeights(){const t=new xe,e=this.geometry.attributes.skinWeight;for(let n=0,s=e.count;n<s;n++){t.fromBufferAttribute(e,n);const r=1/t.manhattanLength();r!==1/0?t.multiplyScalar(r):t.set(1,0,0,0),e.setXYZW(n,t.x,t.y,t.z,t.w)}}updateMatrixWorld(t){super.updateMatrixWorld(t),this.bindMode===ul?this.bindMatrixInverse.copy(this.matrixWorld).invert():this.bindMode===jd?this.bindMatrixInverse.copy(this.bindMatrix).invert():console.warn("THREE.SkinnedMesh: Unrecognized bindMode: "+this.bindMode)}applyBoneTransform(t,e){const n=this.skeleton,s=this.geometry;uh.fromBufferAttribute(s.attributes.skinIndex,t),dh.fromBufferAttribute(s.attributes.skinWeight,t),hh.copy(e).applyMatrix4(this.bindMatrix),e.set(0,0,0);for(let r=0;r<4;r++){const a=dh.getComponent(r);if(a!==0){const o=uh.getComponent(r);fh.multiplyMatrices(n.bones[o].matrixWorld,n.boneInverses[o]),e.addScaledVector(F0.copy(hh).applyMatrix4(fh),a)}}return e.applyMatrix4(this.bindMatrixInverse)}}class wu extends Ne{constructor(){super(),this.isBone=!0,this.type="Bone"}}class Tu extends Ye{constructor(t=null,e=1,n=1,s,r,a,o,c,l=vn,h=vn,u,f){super(null,a,o,c,l,h,s,r,u,f),this.isDataTexture=!0,this.image={data:t,width:e,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}const mh=new jt,k0=new jt;class Yc{constructor(t=[],e=[]){this.uuid=Li(),this.bones=t.slice(0),this.boneInverses=e,this.boneMatrices=null,this.boneTexture=null,this.init()}init(){const t=this.bones,e=this.boneInverses;if(this.boneMatrices=new Float32Array(t.length*16),e.length===0)this.calculateInverses();else if(t.length!==e.length){console.warn("THREE.Skeleton: Number of inverse bone matrices does not match amount of bones."),this.boneInverses=[];for(let n=0,s=this.bones.length;n<s;n++)this.boneInverses.push(new jt)}}calculateInverses(){this.boneInverses.length=0;for(let t=0,e=this.bones.length;t<e;t++){const n=new jt;this.bones[t]&&n.copy(this.bones[t].matrixWorld).invert(),this.boneInverses.push(n)}}pose(){for(let t=0,e=this.bones.length;t<e;t++){const n=this.bones[t];n&&n.matrixWorld.copy(this.boneInverses[t]).invert()}for(let t=0,e=this.bones.length;t<e;t++){const n=this.bones[t];n&&(n.parent&&n.parent.isBone?(n.matrix.copy(n.parent.matrixWorld).invert(),n.matrix.multiply(n.matrixWorld)):n.matrix.copy(n.matrixWorld),n.matrix.decompose(n.position,n.quaternion,n.scale))}}update(){const t=this.bones,e=this.boneInverses,n=this.boneMatrices,s=this.boneTexture;for(let r=0,a=t.length;r<a;r++){const o=t[r]?t[r].matrixWorld:k0;mh.multiplyMatrices(o,e[r]),mh.toArray(n,r*16)}s!==null&&(s.needsUpdate=!0)}clone(){return new Yc(this.bones,this.boneInverses)}computeBoneTexture(){let t=Math.sqrt(this.bones.length*4);t=Math.ceil(t/4)*4,t=Math.max(t,4);const e=new Float32Array(t*t*4);e.set(this.boneMatrices);const n=new Tu(e,t,t,wn,Wn);return n.needsUpdate=!0,this.boneMatrices=e,this.boneTexture=n,this}getBoneByName(t){for(let e=0,n=this.bones.length;e<n;e++){const s=this.bones[e];if(s.name===t)return s}}dispose(){this.boneTexture!==null&&(this.boneTexture.dispose(),this.boneTexture=null)}fromJSON(t,e){this.uuid=t.uuid;for(let n=0,s=t.bones.length;n<s;n++){const r=t.bones[n];let a=e[r];a===void 0&&(console.warn("THREE.Skeleton: No bone found with UUID:",r),a=new wu),this.bones.push(a),this.boneInverses.push(new jt().fromArray(t.boneInverses[n]))}return this.init(),this}toJSON(){const t={metadata:{version:4.6,type:"Skeleton",generator:"Skeleton.toJSON"},bones:[],boneInverses:[]};t.uuid=this.uuid;const e=this.bones,n=this.boneInverses;for(let s=0,r=e.length;s<r;s++){const a=e[s];t.bones.push(a.uuid);const o=n[s];t.boneInverses.push(o.toArray())}return t}}class Bn extends Hn{static get type(){return"LineBasicMaterial"}constructor(t){super(),this.isLineBasicMaterial=!0,this.color=new Kt(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.linewidth=t.linewidth,this.linecap=t.linecap,this.linejoin=t.linejoin,this.fog=t.fog,this}}const Mo=new L,So=new L,gh=new jt,Ks=new Fs,Jr=new di,Ca=new L,_h=new L;class Bs extends Ne{constructor(t=new Pe,e=new Bn){super(),this.isLine=!0,this.type="Line",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[0];for(let s=1,r=e.count;s<r;s++)Mo.fromBufferAttribute(e,s-1),So.fromBufferAttribute(e,s),n[s]=n[s-1],n[s]+=Mo.distanceTo(So);t.setAttribute("lineDistance",new ne(n,1))}else console.warn("THREE.Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}raycast(t,e){const n=this.geometry,s=this.matrixWorld,r=t.params.Line.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),Jr.copy(n.boundingSphere),Jr.applyMatrix4(s),Jr.radius+=r,t.ray.intersectsSphere(Jr)===!1)return;gh.copy(s).invert(),Ks.copy(t.ray).applyMatrix4(gh);const o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=this.isLineSegments?2:1,h=n.index,f=n.attributes.position;if(h!==null){const p=Math.max(0,a.start),g=Math.min(h.count,a.start+a.count);for(let _=p,m=g-1;_<m;_+=l){const d=h.getX(_),w=h.getX(_+1),T=Zr(this,t,Ks,c,d,w);T&&e.push(T)}if(this.isLineLoop){const _=h.getX(g-1),m=h.getX(p),d=Zr(this,t,Ks,c,_,m);d&&e.push(d)}}else{const p=Math.max(0,a.start),g=Math.min(f.count,a.start+a.count);for(let _=p,m=g-1;_<m;_+=l){const d=Zr(this,t,Ks,c,_,_+1);d&&e.push(d)}if(this.isLineLoop){const _=Zr(this,t,Ks,c,g-1,p);_&&e.push(_)}}}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}}function Zr(i,t,e,n,s,r){const a=i.geometry.attributes.position;if(Mo.fromBufferAttribute(a,s),So.fromBufferAttribute(a,r),e.distanceSqToSegment(Mo,So,Ca,_h)>n)return;Ca.applyMatrix4(i.matrixWorld);const c=t.ray.origin.distanceTo(Ca);if(!(c<t.near||c>t.far))return{distance:c,point:_h.clone().applyMatrix4(i.matrixWorld),index:s,face:null,faceIndex:null,barycoord:null,object:i}}const vh=new L,xh=new L;class bo extends Bs{constructor(t,e){super(t,e),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[];for(let s=0,r=e.count;s<r;s+=2)vh.fromBufferAttribute(e,s),xh.fromBufferAttribute(e,s+1),n[s]=s===0?0:n[s-1],n[s+1]=n[s]+vh.distanceTo(xh);t.setAttribute("lineDistance",new ne(n,1))}else console.warn("THREE.LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}}class tr extends Hn{static get type(){return"PointsMaterial"}constructor(t){super(),this.isPointsMaterial=!0,this.color=new Kt(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.alphaMap=t.alphaMap,this.size=t.size,this.sizeAttenuation=t.sizeAttenuation,this.fog=t.fog,this}}const yh=new jt,Ac=new Fs,Qr=new di,to=new L;class Ra extends Ne{constructor(t=new Pe,e=new tr){super(),this.isPoints=!0,this.type="Points",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}raycast(t,e){const n=this.geometry,s=this.matrixWorld,r=t.params.Points.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),Qr.copy(n.boundingSphere),Qr.applyMatrix4(s),Qr.radius+=r,t.ray.intersectsSphere(Qr)===!1)return;yh.copy(s).invert(),Ac.copy(t.ray).applyMatrix4(yh);const o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=n.index,u=n.attributes.position;if(l!==null){const f=Math.max(0,a.start),p=Math.min(l.count,a.start+a.count);for(let g=f,_=p;g<_;g++){const m=l.getX(g);to.fromBufferAttribute(u,m),Mh(to,m,c,s,t,e,this)}}else{const f=Math.max(0,a.start),p=Math.min(u.count,a.start+a.count);for(let g=f,_=p;g<_;g++)to.fromBufferAttribute(u,g),Mh(to,g,c,s,t,e,this)}}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}}function Mh(i,t,e,n,s,r,a){const o=Ac.distanceSqToPoint(i);if(o<e){const c=new L;Ac.closestPointToPoint(i,c),c.applyMatrix4(n);const l=s.ray.origin.distanceTo(c);if(l<s.near||l>s.far)return;r.push({distance:l,distanceToRay:Math.sqrt(o),point:c,index:t,face:null,faceIndex:null,barycoord:null,object:a})}}class qn{constructor(){this.type="Curve",this.arcLengthDivisions=200}getPoint(){return console.warn("THREE.Curve: .getPoint() not implemented."),null}getPointAt(t,e){const n=this.getUtoTmapping(t);return this.getPoint(n,e)}getPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return e}getSpacedPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPointAt(n/t));return e}getLength(){const t=this.getLengths();return t[t.length-1]}getLengths(t=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===t+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;const e=[];let n,s=this.getPoint(0),r=0;e.push(0);for(let a=1;a<=t;a++)n=this.getPoint(a/t),r+=n.distanceTo(s),e.push(r),s=n;return this.cacheArcLengths=e,e}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(t,e){const n=this.getLengths();let s=0;const r=n.length;let a;e?a=e:a=t*n[r-1];let o=0,c=r-1,l;for(;o<=c;)if(s=Math.floor(o+(c-o)/2),l=n[s]-a,l<0)o=s+1;else if(l>0)c=s-1;else{c=s;break}if(s=c,n[s]===a)return s/(r-1);const h=n[s],f=n[s+1]-h,p=(a-h)/f;return(s+p)/(r-1)}getTangent(t,e){let s=t-1e-4,r=t+1e-4;s<0&&(s=0),r>1&&(r=1);const a=this.getPoint(s),o=this.getPoint(r),c=e||(a.isVector2?new At:new L);return c.copy(o).sub(a).normalize(),c}getTangentAt(t,e){const n=this.getUtoTmapping(t);return this.getTangent(n,e)}computeFrenetFrames(t,e){const n=new L,s=[],r=[],a=[],o=new L,c=new jt;for(let p=0;p<=t;p++){const g=p/t;s[p]=this.getTangentAt(g,new L)}r[0]=new L,a[0]=new L;let l=Number.MAX_VALUE;const h=Math.abs(s[0].x),u=Math.abs(s[0].y),f=Math.abs(s[0].z);h<=l&&(l=h,n.set(1,0,0)),u<=l&&(l=u,n.set(0,1,0)),f<=l&&n.set(0,0,1),o.crossVectors(s[0],n).normalize(),r[0].crossVectors(s[0],o),a[0].crossVectors(s[0],r[0]);for(let p=1;p<=t;p++){if(r[p]=r[p-1].clone(),a[p]=a[p-1].clone(),o.crossVectors(s[p-1],s[p]),o.length()>Number.EPSILON){o.normalize();const g=Math.acos(qe(s[p-1].dot(s[p]),-1,1));r[p].applyMatrix4(c.makeRotationAxis(o,g))}a[p].crossVectors(s[p],r[p])}if(e===!0){let p=Math.acos(qe(r[0].dot(r[t]),-1,1));p/=t,s[0].dot(o.crossVectors(r[0],r[t]))>0&&(p=-p);for(let g=1;g<=t;g++)r[g].applyMatrix4(c.makeRotationAxis(s[g],p*g)),a[g].crossVectors(s[g],r[g])}return{tangents:s,normals:r,binormals:a}}clone(){return new this.constructor().copy(this)}copy(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}toJSON(){const t={metadata:{version:4.6,type:"Curve",generator:"Curve.toJSON"}};return t.arcLengthDivisions=this.arcLengthDivisions,t.type=this.type,t}fromJSON(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}}class Au extends qn{constructor(t=0,e=0,n=1,s=1,r=0,a=Math.PI*2,o=!1,c=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=t,this.aY=e,this.xRadius=n,this.yRadius=s,this.aStartAngle=r,this.aEndAngle=a,this.aClockwise=o,this.aRotation=c}getPoint(t,e=new At){const n=e,s=Math.PI*2;let r=this.aEndAngle-this.aStartAngle;const a=Math.abs(r)<Number.EPSILON;for(;r<0;)r+=s;for(;r>s;)r-=s;r<Number.EPSILON&&(a?r=0:r=s),this.aClockwise===!0&&!a&&(r===s?r=-s:r=r-s);const o=this.aStartAngle+t*r;let c=this.aX+this.xRadius*Math.cos(o),l=this.aY+this.yRadius*Math.sin(o);if(this.aRotation!==0){const h=Math.cos(this.aRotation),u=Math.sin(this.aRotation),f=c-this.aX,p=l-this.aY;c=f*h-p*u+this.aX,l=f*u+p*h+this.aY}return n.set(c,l)}copy(t){return super.copy(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}toJSON(){const t=super.toJSON();return t.aX=this.aX,t.aY=this.aY,t.xRadius=this.xRadius,t.yRadius=this.yRadius,t.aStartAngle=this.aStartAngle,t.aEndAngle=this.aEndAngle,t.aClockwise=this.aClockwise,t.aRotation=this.aRotation,t}fromJSON(t){return super.fromJSON(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}}class B0 extends Au{constructor(t,e,n,s,r,a){super(t,e,n,n,s,r,a),this.isArcCurve=!0,this.type="ArcCurve"}}function $c(){let i=0,t=0,e=0,n=0;function s(r,a,o,c){i=r,t=o,e=-3*r+3*a-2*o-c,n=2*r-2*a+o+c}return{initCatmullRom:function(r,a,o,c,l){s(a,o,l*(o-r),l*(c-a))},initNonuniformCatmullRom:function(r,a,o,c,l,h,u){let f=(a-r)/l-(o-r)/(l+h)+(o-a)/h,p=(o-a)/h-(c-a)/(h+u)+(c-o)/u;f*=h,p*=h,s(a,o,f,p)},calc:function(r){const a=r*r,o=a*r;return i+t*r+e*a+n*o}}}const eo=new L,Pa=new $c,La=new $c,Na=new $c;class z0 extends qn{constructor(t=[],e=!1,n="centripetal",s=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=t,this.closed=e,this.curveType=n,this.tension=s}getPoint(t,e=new L){const n=e,s=this.points,r=s.length,a=(r-(this.closed?0:1))*t;let o=Math.floor(a),c=a-o;this.closed?o+=o>0?0:(Math.floor(Math.abs(o)/r)+1)*r:c===0&&o===r-1&&(o=r-2,c=1);let l,h;this.closed||o>0?l=s[(o-1)%r]:(eo.subVectors(s[0],s[1]).add(s[0]),l=eo);const u=s[o%r],f=s[(o+1)%r];if(this.closed||o+2<r?h=s[(o+2)%r]:(eo.subVectors(s[r-1],s[r-2]).add(s[r-1]),h=eo),this.curveType==="centripetal"||this.curveType==="chordal"){const p=this.curveType==="chordal"?.5:.25;let g=Math.pow(l.distanceToSquared(u),p),_=Math.pow(u.distanceToSquared(f),p),m=Math.pow(f.distanceToSquared(h),p);_<1e-4&&(_=1),g<1e-4&&(g=_),m<1e-4&&(m=_),Pa.initNonuniformCatmullRom(l.x,u.x,f.x,h.x,g,_,m),La.initNonuniformCatmullRom(l.y,u.y,f.y,h.y,g,_,m),Na.initNonuniformCatmullRom(l.z,u.z,f.z,h.z,g,_,m)}else this.curveType==="catmullrom"&&(Pa.initCatmullRom(l.x,u.x,f.x,h.x,this.tension),La.initCatmullRom(l.y,u.y,f.y,h.y,this.tension),Na.initCatmullRom(l.z,u.z,f.z,h.z,this.tension));return n.set(Pa.calc(c),La.calc(c),Na.calc(c)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(s.clone())}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const s=this.points[e];t.points.push(s.toArray())}return t.closed=this.closed,t.curveType=this.curveType,t.tension=this.tension,t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(new L().fromArray(s))}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}}function Sh(i,t,e,n,s){const r=(n-t)*.5,a=(s-e)*.5,o=i*i,c=i*o;return(2*e-2*n+r+a)*c+(-3*e+3*n-2*r-a)*o+r*i+e}function V0(i,t){const e=1-i;return e*e*t}function H0(i,t){return 2*(1-i)*i*t}function G0(i,t){return i*i*t}function rr(i,t,e,n){return V0(i,t)+H0(i,e)+G0(i,n)}function W0(i,t){const e=1-i;return e*e*e*t}function X0(i,t){const e=1-i;return 3*e*e*i*t}function q0(i,t){return 3*(1-i)*i*i*t}function j0(i,t){return i*i*i*t}function or(i,t,e,n,s){return W0(i,t)+X0(i,e)+q0(i,n)+j0(i,s)}class Y0 extends qn{constructor(t=new At,e=new At,n=new At,s=new At){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=t,this.v1=e,this.v2=n,this.v3=s}getPoint(t,e=new At){const n=e,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(or(t,s.x,r.x,a.x,o.x),or(t,s.y,r.y,a.y,o.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class $0 extends qn{constructor(t=new L,e=new L,n=new L,s=new L){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=t,this.v1=e,this.v2=n,this.v3=s}getPoint(t,e=new L){const n=e,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(or(t,s.x,r.x,a.x,o.x),or(t,s.y,r.y,a.y,o.y),or(t,s.z,r.z,a.z,o.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class K0 extends qn{constructor(t=new At,e=new At){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=t,this.v2=e}getPoint(t,e=new At){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new At){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class Cu extends qn{constructor(t=new L,e=new L){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=t,this.v2=e}getPoint(t,e=new L){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new L){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class J0 extends qn{constructor(t=new At,e=new At,n=new At){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new At){const n=e,s=this.v0,r=this.v1,a=this.v2;return n.set(rr(t,s.x,r.x,a.x),rr(t,s.y,r.y,a.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class Ru extends qn{constructor(t=new L,e=new L,n=new L){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new L){const n=e,s=this.v0,r=this.v1,a=this.v2;return n.set(rr(t,s.x,r.x,a.x),rr(t,s.y,r.y,a.y),rr(t,s.z,r.z,a.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class Z0 extends qn{constructor(t=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=t}getPoint(t,e=new At){const n=e,s=this.points,r=(s.length-1)*t,a=Math.floor(r),o=r-a,c=s[a===0?a:a-1],l=s[a],h=s[a>s.length-2?s.length-1:a+1],u=s[a>s.length-3?s.length-1:a+2];return n.set(Sh(o,c.x,l.x,h.x,u.x),Sh(o,c.y,l.y,h.y,u.y)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(s.clone())}return this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const s=this.points[e];t.points.push(s.toArray())}return t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(new At().fromArray(s))}return this}}var Cc=Object.freeze({__proto__:null,ArcCurve:B0,CatmullRomCurve3:z0,CubicBezierCurve:Y0,CubicBezierCurve3:$0,EllipseCurve:Au,LineCurve:K0,LineCurve3:Cu,QuadraticBezierCurve:J0,QuadraticBezierCurve3:Ru,SplineCurve:Z0});class Q0 extends qn{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(t){this.curves.push(t)}closePath(){const t=this.curves[0].getPoint(0),e=this.curves[this.curves.length-1].getPoint(1);if(!t.equals(e)){const n=t.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new Cc[n](e,t))}return this}getPoint(t,e){const n=t*this.getLength(),s=this.getCurveLengths();let r=0;for(;r<s.length;){if(s[r]>=n){const a=s[r]-n,o=this.curves[r],c=o.getLength(),l=c===0?0:1-a/c;return o.getPointAt(l,e)}r++}return null}getLength(){const t=this.getCurveLengths();return t[t.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;const t=[];let e=0;for(let n=0,s=this.curves.length;n<s;n++)e+=this.curves[n].getLength(),t.push(e);return this.cacheLengths=t,t}getSpacedPoints(t=40){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return this.autoClose&&e.push(e[0]),e}getPoints(t=12){const e=[];let n;for(let s=0,r=this.curves;s<r.length;s++){const a=r[s],o=a.isEllipseCurve?t*2:a.isLineCurve||a.isLineCurve3?1:a.isSplineCurve?t*a.points.length:t,c=a.getPoints(o);for(let l=0;l<c.length;l++){const h=c[l];n&&n.equals(h)||(e.push(h),n=h)}}return this.autoClose&&e.length>1&&!e[e.length-1].equals(e[0])&&e.push(e[0]),e}copy(t){super.copy(t),this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const s=t.curves[e];this.curves.push(s.clone())}return this.autoClose=t.autoClose,this}toJSON(){const t=super.toJSON();t.autoClose=this.autoClose,t.curves=[];for(let e=0,n=this.curves.length;e<n;e++){const s=this.curves[e];t.curves.push(s.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.autoClose=t.autoClose,this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const s=t.curves[e];this.curves.push(new Cc[s.type]().fromJSON(s))}return this}}class Eo extends Pe{constructor(t=1,e=32,n=0,s=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius:t,segments:e,thetaStart:n,thetaLength:s},e=Math.max(3,e);const r=[],a=[],o=[],c=[],l=new L,h=new At;a.push(0,0,0),o.push(0,0,1),c.push(.5,.5);for(let u=0,f=3;u<=e;u++,f+=3){const p=n+u/e*s;l.x=t*Math.cos(p),l.y=t*Math.sin(p),a.push(l.x,l.y,l.z),o.push(0,0,1),h.x=(a[f]/t+1)/2,h.y=(a[f+1]/t+1)/2,c.push(h.x,h.y)}for(let u=1;u<=e;u++)r.push(u,u+1,0);this.setIndex(r),this.setAttribute("position",new ne(a,3)),this.setAttribute("normal",new ne(o,3)),this.setAttribute("uv",new ne(c,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Eo(t.radius,t.segments,t.thetaStart,t.thetaLength)}}class zs extends Pe{constructor(t=1,e=1,n=1,s=32,r=1,a=!1,o=0,c=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:t,radiusBottom:e,height:n,radialSegments:s,heightSegments:r,openEnded:a,thetaStart:o,thetaLength:c};const l=this;s=Math.floor(s),r=Math.floor(r);const h=[],u=[],f=[],p=[];let g=0;const _=[],m=n/2;let d=0;w(),a===!1&&(t>0&&T(!0),e>0&&T(!1)),this.setIndex(h),this.setAttribute("position",new ne(u,3)),this.setAttribute("normal",new ne(f,3)),this.setAttribute("uv",new ne(p,2));function w(){const M=new L,F=new L;let P=0;const N=(e-t)/n;for(let D=0;D<=r;D++){const y=[],S=D/r,U=S*(e-t)+t;for(let k=0;k<=s;k++){const H=k/s,J=H*c+o,Q=Math.sin(J),O=Math.cos(J);F.x=U*Q,F.y=-S*n+m,F.z=U*O,u.push(F.x,F.y,F.z),M.set(Q,N,O).normalize(),f.push(M.x,M.y,M.z),p.push(H,1-S),y.push(g++)}_.push(y)}for(let D=0;D<s;D++)for(let y=0;y<r;y++){const S=_[y][D],U=_[y+1][D],k=_[y+1][D+1],H=_[y][D+1];(t>0||y!==0)&&(h.push(S,U,H),P+=3),(e>0||y!==r-1)&&(h.push(U,k,H),P+=3)}l.addGroup(d,P,0),d+=P}function T(M){const F=g,P=new At,N=new L;let D=0;const y=M===!0?t:e,S=M===!0?1:-1;for(let k=1;k<=s;k++)u.push(0,m*S,0),f.push(0,S,0),p.push(.5,.5),g++;const U=g;for(let k=0;k<=s;k++){const J=k/s*c+o,Q=Math.cos(J),O=Math.sin(J);N.x=y*O,N.y=m*S,N.z=y*Q,u.push(N.x,N.y,N.z),f.push(0,S,0),P.x=Q*.5+.5,P.y=O*.5*S+.5,p.push(P.x,P.y),g++}for(let k=0;k<s;k++){const H=F+k,J=U+k;M===!0?h.push(J,J+1,H):h.push(J+1,J,H),D+=3}l.addGroup(d,D,M===!0?1:2),d+=D}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new zs(t.radiusTop,t.radiusBottom,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class Kc extends zs{constructor(t=1,e=1,n=32,s=1,r=!1,a=0,o=Math.PI*2){super(0,t,e,n,s,r,a,o),this.type="ConeGeometry",this.parameters={radius:t,height:e,radialSegments:n,heightSegments:s,openEnded:r,thetaStart:a,thetaLength:o}}static fromJSON(t){return new Kc(t.radius,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class wo extends Pe{constructor(t=.5,e=1,n=32,s=1,r=0,a=Math.PI*2){super(),this.type="RingGeometry",this.parameters={innerRadius:t,outerRadius:e,thetaSegments:n,phiSegments:s,thetaStart:r,thetaLength:a},n=Math.max(3,n),s=Math.max(1,s);const o=[],c=[],l=[],h=[];let u=t;const f=(e-t)/s,p=new L,g=new At;for(let _=0;_<=s;_++){for(let m=0;m<=n;m++){const d=r+m/n*a;p.x=u*Math.cos(d),p.y=u*Math.sin(d),c.push(p.x,p.y,p.z),l.push(0,0,1),g.x=(p.x/e+1)/2,g.y=(p.y/e+1)/2,h.push(g.x,g.y)}u+=f}for(let _=0;_<s;_++){const m=_*(n+1);for(let d=0;d<n;d++){const w=d+m,T=w,M=w+n+1,F=w+n+2,P=w+1;o.push(T,M,P),o.push(M,F,P)}}this.setIndex(o),this.setAttribute("position",new ne(c,3)),this.setAttribute("normal",new ne(l,3)),this.setAttribute("uv",new ne(h,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new wo(t.innerRadius,t.outerRadius,t.thetaSegments,t.phiSegments,t.thetaStart,t.thetaLength)}}class li extends Pe{constructor(t=1,e=32,n=16,s=0,r=Math.PI*2,a=0,o=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:t,widthSegments:e,heightSegments:n,phiStart:s,phiLength:r,thetaStart:a,thetaLength:o},e=Math.max(3,Math.floor(e)),n=Math.max(2,Math.floor(n));const c=Math.min(a+o,Math.PI);let l=0;const h=[],u=new L,f=new L,p=[],g=[],_=[],m=[];for(let d=0;d<=n;d++){const w=[],T=d/n;let M=0;d===0&&a===0?M=.5/e:d===n&&c===Math.PI&&(M=-.5/e);for(let F=0;F<=e;F++){const P=F/e;u.x=-t*Math.cos(s+P*r)*Math.sin(a+T*o),u.y=t*Math.cos(a+T*o),u.z=t*Math.sin(s+P*r)*Math.sin(a+T*o),g.push(u.x,u.y,u.z),f.copy(u).normalize(),_.push(f.x,f.y,f.z),m.push(P+M,1-T),w.push(l++)}h.push(w)}for(let d=0;d<n;d++)for(let w=0;w<e;w++){const T=h[d][w+1],M=h[d][w],F=h[d+1][w],P=h[d+1][w+1];(d!==0||a>0)&&p.push(T,M,P),(d!==n-1||c<Math.PI)&&p.push(M,F,P)}this.setIndex(p),this.setAttribute("position",new ne(g,3)),this.setAttribute("normal",new ne(_,3)),this.setAttribute("uv",new ne(m,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new li(t.radius,t.widthSegments,t.heightSegments,t.phiStart,t.phiLength,t.thetaStart,t.thetaLength)}}class Jc extends Pe{constructor(t=new Ru(new L(-1,-1,0),new L(-1,1,0),new L(1,1,0)),e=64,n=1,s=8,r=!1){super(),this.type="TubeGeometry",this.parameters={path:t,tubularSegments:e,radius:n,radialSegments:s,closed:r};const a=t.computeFrenetFrames(e,r);this.tangents=a.tangents,this.normals=a.normals,this.binormals=a.binormals;const o=new L,c=new L,l=new At;let h=new L;const u=[],f=[],p=[],g=[];_(),this.setIndex(g),this.setAttribute("position",new ne(u,3)),this.setAttribute("normal",new ne(f,3)),this.setAttribute("uv",new ne(p,2));function _(){for(let T=0;T<e;T++)m(T);m(r===!1?e:0),w(),d()}function m(T){h=t.getPointAt(T/e,h);const M=a.normals[T],F=a.binormals[T];for(let P=0;P<=s;P++){const N=P/s*Math.PI*2,D=Math.sin(N),y=-Math.cos(N);c.x=y*M.x+D*F.x,c.y=y*M.y+D*F.y,c.z=y*M.z+D*F.z,c.normalize(),f.push(c.x,c.y,c.z),o.x=h.x+n*c.x,o.y=h.y+n*c.y,o.z=h.z+n*c.z,u.push(o.x,o.y,o.z)}}function d(){for(let T=1;T<=e;T++)for(let M=1;M<=s;M++){const F=(s+1)*(T-1)+(M-1),P=(s+1)*T+(M-1),N=(s+1)*T+M,D=(s+1)*(T-1)+M;g.push(F,P,D),g.push(P,N,D)}}function w(){for(let T=0;T<=e;T++)for(let M=0;M<=s;M++)l.x=T/e,l.y=M/s,p.push(l.x,l.y)}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){const t=super.toJSON();return t.path=this.parameters.path.toJSON(),t}static fromJSON(t){return new Jc(new Cc[t.path.type]().fromJSON(t.path),t.tubularSegments,t.radius,t.radialSegments,t.closed)}}class tv extends Hn{static get type(){return"MeshStandardMaterial"}constructor(t){super(),this.isMeshStandardMaterial=!0,this.defines={STANDARD:""},this.color=new Kt(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Kt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Oo,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new fn,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.defines={STANDARD:""},this.color.copy(t.color),this.roughness=t.roughness,this.metalness=t.metalness,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.roughnessMap=t.roughnessMap,this.metalnessMap=t.metalnessMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.envMapIntensity=t.envMapIntensity,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}class Ms extends Hn{static get type(){return"MeshPhongMaterial"}constructor(t){super(),this.isMeshPhongMaterial=!0,this.color=new Kt(16777215),this.specular=new Kt(1118481),this.shininess=30,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Kt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Oo,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new fn,this.combine=Uo,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.specular.copy(t.specular),this.shininess=t.shininess,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}class ev extends Hn{static get type(){return"MeshLambertMaterial"}constructor(t){super(),this.isMeshLambertMaterial=!0,this.color=new Kt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Kt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Oo,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new fn,this.combine=Uo,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}function no(i,t,e){return!i||!e&&i.constructor===t?i:typeof t.BYTES_PER_ELEMENT=="number"?new t(i):Array.prototype.slice.call(i)}function nv(i){return ArrayBuffer.isView(i)&&!(i instanceof DataView)}function iv(i){function t(s,r){return i[s]-i[r]}const e=i.length,n=new Array(e);for(let s=0;s!==e;++s)n[s]=s;return n.sort(t),n}function bh(i,t,e){const n=i.length,s=new i.constructor(n);for(let r=0,a=0;a!==n;++r){const o=e[r]*t;for(let c=0;c!==t;++c)s[a++]=i[o+c]}return s}function Pu(i,t,e,n){let s=1,r=i[0];for(;r!==void 0&&r[n]===void 0;)r=i[s++];if(r===void 0)return;let a=r[n];if(a!==void 0)if(Array.isArray(a))do a=r[n],a!==void 0&&(t.push(r.time),e.push.apply(e,a)),r=i[s++];while(r!==void 0);else if(a.toArray!==void 0)do a=r[n],a!==void 0&&(t.push(r.time),a.toArray(e,e.length)),r=i[s++];while(r!==void 0);else do a=r[n],a!==void 0&&(t.push(r.time),e.push(a)),r=i[s++];while(r!==void 0)}class Vo{constructor(t,e,n,s){this.parameterPositions=t,this._cachedIndex=0,this.resultBuffer=s!==void 0?s:new e.constructor(n),this.sampleValues=e,this.valueSize=n,this.settings=null,this.DefaultSettings_={}}evaluate(t){const e=this.parameterPositions;let n=this._cachedIndex,s=e[n],r=e[n-1];n:{t:{let a;e:{i:if(!(t<s)){for(let o=n+2;;){if(s===void 0){if(t<r)break i;return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}if(n===o)break;if(r=s,s=e[++n],t<s)break t}a=e.length;break e}if(!(t>=r)){const o=e[1];t<o&&(n=2,r=o);for(let c=n-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(n===c)break;if(s=r,r=e[--n-1],t>=r)break t}a=n,n=0;break e}break n}for(;n<a;){const o=n+a>>>1;t<e[o]?a=o:n=o+1}if(s=e[n],r=e[n-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(s===void 0)return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}this._cachedIndex=n,this.intervalChanged_(n,r,s)}return this.interpolate_(n,r,t,s)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(t){const e=this.resultBuffer,n=this.sampleValues,s=this.valueSize,r=t*s;for(let a=0;a!==s;++a)e[a]=n[r+a];return e}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}}class sv extends Vo{constructor(t,e,n,s){super(t,e,n,s),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:dl,endingEnd:dl}}intervalChanged_(t,e,n){const s=this.parameterPositions;let r=t-2,a=t+1,o=s[r],c=s[a];if(o===void 0)switch(this.getSettings_().endingStart){case fl:r=t,o=2*e-n;break;case pl:r=s.length-2,o=e+s[r]-s[r+1];break;default:r=t,o=n}if(c===void 0)switch(this.getSettings_().endingEnd){case fl:a=t,c=2*n-e;break;case pl:a=1,c=n+s[1]-s[0];break;default:a=t-1,c=e}const l=(n-e)*.5,h=this.valueSize;this._weightPrev=l/(e-o),this._weightNext=l/(c-n),this._offsetPrev=r*h,this._offsetNext=a*h}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=t*o,l=c-o,h=this._offsetPrev,u=this._offsetNext,f=this._weightPrev,p=this._weightNext,g=(n-e)/(s-e),_=g*g,m=_*g,d=-f*m+2*f*_-f*g,w=(1+f)*m+(-1.5-2*f)*_+(-.5+f)*g+1,T=(-1-p)*m+(1.5+p)*_+.5*g,M=p*m-p*_;for(let F=0;F!==o;++F)r[F]=d*a[h+F]+w*a[l+F]+T*a[c+F]+M*a[u+F];return r}}class rv extends Vo{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=t*o,l=c-o,h=(n-e)/(s-e),u=1-h;for(let f=0;f!==o;++f)r[f]=a[l+f]*u+a[c+f]*h;return r}}class ov extends Vo{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t){return this.copySampleValue_(t-1)}}class jn{constructor(t,e,n,s){if(t===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(e===void 0||e.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+t);this.name=t,this.times=no(e,this.TimeBufferType),this.values=no(n,this.ValueBufferType),this.setInterpolation(s||this.DefaultInterpolation)}static toJSON(t){const e=t.constructor;let n;if(e.toJSON!==this.toJSON)n=e.toJSON(t);else{n={name:t.name,times:no(t.times,Array),values:no(t.values,Array)};const s=t.getInterpolation();s!==t.DefaultInterpolation&&(n.interpolation=s)}return n.type=t.ValueTypeName,n}InterpolantFactoryMethodDiscrete(t){return new ov(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodLinear(t){return new rv(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodSmooth(t){return new sv(this.times,this.values,this.getValueSize(),t)}setInterpolation(t){let e;switch(t){case xo:e=this.InterpolantFactoryMethodDiscrete;break;case wc:e=this.InterpolantFactoryMethodLinear;break;case Zo:e=this.InterpolantFactoryMethodSmooth;break}if(e===void 0){const n="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(t!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(n);return console.warn("THREE.KeyframeTrack:",n),this}return this.createInterpolant=e,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return xo;case this.InterpolantFactoryMethodLinear:return wc;case this.InterpolantFactoryMethodSmooth:return Zo}}getValueSize(){return this.values.length/this.times.length}shift(t){if(t!==0){const e=this.times;for(let n=0,s=e.length;n!==s;++n)e[n]+=t}return this}scale(t){if(t!==1){const e=this.times;for(let n=0,s=e.length;n!==s;++n)e[n]*=t}return this}trim(t,e){const n=this.times,s=n.length;let r=0,a=s-1;for(;r!==s&&n[r]<t;)++r;for(;a!==-1&&n[a]>e;)--a;if(++a,r!==0||a!==s){r>=a&&(a=Math.max(a,1),r=a-1);const o=this.getValueSize();this.times=n.slice(r,a),this.values=this.values.slice(r*o,a*o)}return this}validate(){let t=!0;const e=this.getValueSize();e-Math.floor(e)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),t=!1);const n=this.times,s=this.values,r=n.length;r===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),t=!1);let a=null;for(let o=0;o!==r;o++){const c=n[o];if(typeof c=="number"&&isNaN(c)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,o,c),t=!1;break}if(a!==null&&a>c){console.error("THREE.KeyframeTrack: Out of order keys.",this,o,c,a),t=!1;break}a=c}if(s!==void 0&&nv(s))for(let o=0,c=s.length;o!==c;++o){const l=s[o];if(isNaN(l)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,o,l),t=!1;break}}return t}optimize(){const t=this.times.slice(),e=this.values.slice(),n=this.getValueSize(),s=this.getInterpolation()===Zo,r=t.length-1;let a=1;for(let o=1;o<r;++o){let c=!1;const l=t[o],h=t[o+1];if(l!==h&&(o!==1||l!==t[0]))if(s)c=!0;else{const u=o*n,f=u-n,p=u+n;for(let g=0;g!==n;++g){const _=e[u+g];if(_!==e[f+g]||_!==e[p+g]){c=!0;break}}}if(c){if(o!==a){t[a]=t[o];const u=o*n,f=a*n;for(let p=0;p!==n;++p)e[f+p]=e[u+p]}++a}}if(r>0){t[a]=t[r];for(let o=r*n,c=a*n,l=0;l!==n;++l)e[c+l]=e[o+l];++a}return a!==t.length?(this.times=t.slice(0,a),this.values=e.slice(0,a*n)):(this.times=t,this.values=e),this}clone(){const t=this.times.slice(),e=this.values.slice(),n=this.constructor,s=new n(this.name,t,e);return s.createInterpolant=this.createInterpolant,s}}jn.prototype.TimeBufferType=Float32Array;jn.prototype.ValueBufferType=Float32Array;jn.prototype.DefaultInterpolation=wc;class Vs extends jn{constructor(t,e,n){super(t,e,n)}}Vs.prototype.ValueTypeName="bool";Vs.prototype.ValueBufferType=Array;Vs.prototype.DefaultInterpolation=xo;Vs.prototype.InterpolantFactoryMethodLinear=void 0;Vs.prototype.InterpolantFactoryMethodSmooth=void 0;class Lu extends jn{}Lu.prototype.ValueTypeName="color";class To extends jn{}To.prototype.ValueTypeName="number";class av extends Vo{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=(n-e)/(s-e);let l=t*o;for(let h=l+o;l!==h;l+=4)Vn.slerpFlat(r,0,a,l-o,a,l,c);return r}}class _r extends jn{InterpolantFactoryMethodLinear(t){return new av(this.times,this.values,this.getValueSize(),t)}}_r.prototype.ValueTypeName="quaternion";_r.prototype.InterpolantFactoryMethodSmooth=void 0;class Hs extends jn{constructor(t,e,n){super(t,e,n)}}Hs.prototype.ValueTypeName="string";Hs.prototype.ValueBufferType=Array;Hs.prototype.DefaultInterpolation=xo;Hs.prototype.InterpolantFactoryMethodLinear=void 0;Hs.prototype.InterpolantFactoryMethodSmooth=void 0;class Ns extends jn{}Ns.prototype.ValueTypeName="vector";class Eh{constructor(t="",e=-1,n=[],s=$d){this.name=t,this.tracks=n,this.duration=e,this.blendMode=s,this.uuid=Li(),this.duration<0&&this.resetDuration()}static parse(t){const e=[],n=t.tracks,s=1/(t.fps||1);for(let a=0,o=n.length;a!==o;++a)e.push(lv(n[a]).scale(s));const r=new this(t.name,t.duration,e,t.blendMode);return r.uuid=t.uuid,r}static toJSON(t){const e=[],n=t.tracks,s={name:t.name,duration:t.duration,tracks:e,uuid:t.uuid,blendMode:t.blendMode};for(let r=0,a=n.length;r!==a;++r)e.push(jn.toJSON(n[r]));return s}static CreateFromMorphTargetSequence(t,e,n,s){const r=e.length,a=[];for(let o=0;o<r;o++){let c=[],l=[];c.push((o+r-1)%r,o,(o+1)%r),l.push(0,1,0);const h=iv(c);c=bh(c,1,h),l=bh(l,1,h),!s&&c[0]===0&&(c.push(r),l.push(l[0])),a.push(new To(".morphTargetInfluences["+e[o].name+"]",c,l).scale(1/n))}return new this(t,-1,a)}static findByName(t,e){let n=t;if(!Array.isArray(t)){const s=t;n=s.geometry&&s.geometry.animations||s.animations}for(let s=0;s<n.length;s++)if(n[s].name===e)return n[s];return null}static CreateClipsFromMorphTargetSequences(t,e,n){const s={},r=/^([\w-]*?)([\d]+)$/;for(let o=0,c=t.length;o<c;o++){const l=t[o],h=l.name.match(r);if(h&&h.length>1){const u=h[1];let f=s[u];f||(s[u]=f=[]),f.push(l)}}const a=[];for(const o in s)a.push(this.CreateFromMorphTargetSequence(o,s[o],e,n));return a}static parseAnimation(t,e){if(!t)return console.error("THREE.AnimationClip: No animation in JSONLoader data."),null;const n=function(u,f,p,g,_){if(p.length!==0){const m=[],d=[];Pu(p,m,d,g),m.length!==0&&_.push(new u(f,m,d))}},s=[],r=t.name||"default",a=t.fps||30,o=t.blendMode;let c=t.length||-1;const l=t.hierarchy||[];for(let u=0;u<l.length;u++){const f=l[u].keys;if(!(!f||f.length===0))if(f[0].morphTargets){const p={};let g;for(g=0;g<f.length;g++)if(f[g].morphTargets)for(let _=0;_<f[g].morphTargets.length;_++)p[f[g].morphTargets[_]]=-1;for(const _ in p){const m=[],d=[];for(let w=0;w!==f[g].morphTargets.length;++w){const T=f[g];m.push(T.time),d.push(T.morphTarget===_?1:0)}s.push(new To(".morphTargetInfluence["+_+"]",m,d))}c=p.length*a}else{const p=".bones["+e[u].name+"]";n(Ns,p+".position",f,"pos",s),n(_r,p+".quaternion",f,"rot",s),n(Ns,p+".scale",f,"scl",s)}}return s.length===0?null:new this(r,c,s,o)}resetDuration(){const t=this.tracks;let e=0;for(let n=0,s=t.length;n!==s;++n){const r=this.tracks[n];e=Math.max(e,r.times[r.times.length-1])}return this.duration=e,this}trim(){for(let t=0;t<this.tracks.length;t++)this.tracks[t].trim(0,this.duration);return this}validate(){let t=!0;for(let e=0;e<this.tracks.length;e++)t=t&&this.tracks[e].validate();return t}optimize(){for(let t=0;t<this.tracks.length;t++)this.tracks[t].optimize();return this}clone(){const t=[];for(let e=0;e<this.tracks.length;e++)t.push(this.tracks[e].clone());return new this.constructor(this.name,this.duration,t,this.blendMode)}toJSON(){return this.constructor.toJSON(this)}}function cv(i){switch(i.toLowerCase()){case"scalar":case"double":case"float":case"number":case"integer":return To;case"vector":case"vector2":case"vector3":case"vector4":return Ns;case"color":return Lu;case"quaternion":return _r;case"bool":case"boolean":return Vs;case"string":return Hs}throw new Error("THREE.KeyframeTrack: Unsupported typeName: "+i)}function lv(i){if(i.type===void 0)throw new Error("THREE.KeyframeTrack: track type undefined, can not parse");const t=cv(i.type);if(i.times===void 0){const e=[],n=[];Pu(i.keys,e,n,"value"),i.times=e,i.values=n}return t.parse!==void 0?t.parse(i):new t(i.name,i.times,i.values,i.interpolation)}const Ao={enabled:!1,files:{},add:function(i,t){this.enabled!==!1&&(this.files[i]=t)},get:function(i){if(this.enabled!==!1)return this.files[i]},remove:function(i){delete this.files[i]},clear:function(){this.files={}}};class Nu{constructor(t,e,n){const s=this;let r=!1,a=0,o=0,c;const l=[];this.onStart=void 0,this.onLoad=t,this.onProgress=e,this.onError=n,this.itemStart=function(h){o++,r===!1&&s.onStart!==void 0&&s.onStart(h,a,o),r=!0},this.itemEnd=function(h){a++,s.onProgress!==void 0&&s.onProgress(h,a,o),a===o&&(r=!1,s.onLoad!==void 0&&s.onLoad())},this.itemError=function(h){s.onError!==void 0&&s.onError(h)},this.resolveURL=function(h){return c?c(h):h},this.setURLModifier=function(h){return c=h,this},this.addHandler=function(h,u){return l.push(h,u),this},this.removeHandler=function(h){const u=l.indexOf(h);return u!==-1&&l.splice(u,2),this},this.getHandler=function(h){for(let u=0,f=l.length;u<f;u+=2){const p=l[u],g=l[u+1];if(p.global&&(p.lastIndex=0),p.test(h))return g}return null}}}const Du=new Nu;class hi{constructor(t){this.manager=t!==void 0?t:Du,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(t,e){const n=this;return new Promise(function(s,r){n.load(t,s,e,r)})}parse(){}setCrossOrigin(t){return this.crossOrigin=t,this}setWithCredentials(t){return this.withCredentials=t,this}setPath(t){return this.path=t,this}setResourcePath(t){return this.resourcePath=t,this}setRequestHeader(t){return this.requestHeader=t,this}}hi.DEFAULT_MATERIAL_NAME="__DEFAULT";const ei={};class hv extends Error{constructor(t,e){super(t),this.response=e}}class Ho extends hi{constructor(t){super(t)}load(t,e,n,s){t===void 0&&(t=""),this.path!==void 0&&(t=this.path+t),t=this.manager.resolveURL(t);const r=Ao.get(t);if(r!==void 0)return this.manager.itemStart(t),setTimeout(()=>{e&&e(r),this.manager.itemEnd(t)},0),r;if(ei[t]!==void 0){ei[t].push({onLoad:e,onProgress:n,onError:s});return}ei[t]=[],ei[t].push({onLoad:e,onProgress:n,onError:s});const a=new Request(t,{headers:new Headers(this.requestHeader),credentials:this.withCredentials?"include":"same-origin"}),o=this.mimeType,c=this.responseType;fetch(a).then(l=>{if(l.status===200||l.status===0){if(l.status===0&&console.warn("THREE.FileLoader: HTTP Status 0 received."),typeof ReadableStream>"u"||l.body===void 0||l.body.getReader===void 0)return l;const h=ei[t],u=l.body.getReader(),f=l.headers.get("X-File-Size")||l.headers.get("Content-Length"),p=f?parseInt(f):0,g=p!==0;let _=0;const m=new ReadableStream({start(d){w();function w(){u.read().then(({done:T,value:M})=>{if(T)d.close();else{_+=M.byteLength;const F=new ProgressEvent("progress",{lengthComputable:g,loaded:_,total:p});for(let P=0,N=h.length;P<N;P++){const D=h[P];D.onProgress&&D.onProgress(F)}d.enqueue(M),w()}},T=>{d.error(T)})}}});return new Response(m)}else throw new hv(`fetch for "${l.url}" responded with ${l.status}: ${l.statusText}`,l)}).then(l=>{switch(c){case"arraybuffer":return l.arrayBuffer();case"blob":return l.blob();case"document":return l.text().then(h=>new DOMParser().parseFromString(h,o));case"json":return l.json();default:if(o===void 0)return l.text();{const u=/charset="?([^;"\s]*)"?/i.exec(o),f=u&&u[1]?u[1].toLowerCase():void 0,p=new TextDecoder(f);return l.arrayBuffer().then(g=>p.decode(g))}}}).then(l=>{Ao.add(t,l);const h=ei[t];delete ei[t];for(let u=0,f=h.length;u<f;u++){const p=h[u];p.onLoad&&p.onLoad(l)}}).catch(l=>{const h=ei[t];if(h===void 0)throw this.manager.itemError(t),l;delete ei[t];for(let u=0,f=h.length;u<f;u++){const p=h[u];p.onError&&p.onError(l)}this.manager.itemError(t)}).finally(()=>{this.manager.itemEnd(t)}),this.manager.itemStart(t)}setResponseType(t){return this.responseType=t,this}setMimeType(t){return this.mimeType=t,this}}class uv extends hi{constructor(t){super(t)}load(t,e,n,s){this.path!==void 0&&(t=this.path+t),t=this.manager.resolveURL(t);const r=this,a=Ao.get(t);if(a!==void 0)return r.manager.itemStart(t),setTimeout(function(){e&&e(a),r.manager.itemEnd(t)},0),a;const o=lr("img");function c(){h(),Ao.add(t,this),e&&e(this),r.manager.itemEnd(t)}function l(u){h(),s&&s(u),r.manager.itemError(t),r.manager.itemEnd(t)}function h(){o.removeEventListener("load",c,!1),o.removeEventListener("error",l,!1)}return o.addEventListener("load",c,!1),o.addEventListener("error",l,!1),t.slice(0,5)!=="data:"&&this.crossOrigin!==void 0&&(o.crossOrigin=this.crossOrigin),r.manager.itemStart(t),o.src=t,o}}class dv extends hi{constructor(t){super(t)}load(t,e,n,s){const r=this,a=new Tu,o=new Ho(this.manager);return o.setResponseType("arraybuffer"),o.setRequestHeader(this.requestHeader),o.setPath(this.path),o.setWithCredentials(r.withCredentials),o.load(t,function(c){let l;try{l=r.parse(c)}catch(h){if(s!==void 0)s(h);else{console.error(h);return}}l.image!==void 0?a.image=l.image:l.data!==void 0&&(a.image.width=l.width,a.image.height=l.height,a.image.data=l.data),a.wrapS=l.wrapS!==void 0?l.wrapS:On,a.wrapT=l.wrapT!==void 0?l.wrapT:On,a.magFilter=l.magFilter!==void 0?l.magFilter:_n,a.minFilter=l.minFilter!==void 0?l.minFilter:_n,a.anisotropy=l.anisotropy!==void 0?l.anisotropy:1,l.colorSpace!==void 0&&(a.colorSpace=l.colorSpace),l.flipY!==void 0&&(a.flipY=l.flipY),l.format!==void 0&&(a.format=l.format),l.type!==void 0&&(a.type=l.type),l.mipmaps!==void 0&&(a.mipmaps=l.mipmaps,a.minFilter=si),l.mipmapCount===1&&(a.minFilter=_n),l.generateMipmaps!==void 0&&(a.generateMipmaps=l.generateMipmaps),a.needsUpdate=!0,e&&e(a,l)},n,s),a}}class Iu extends hi{constructor(t){super(t)}load(t,e,n,s){const r=new Ye,a=new uv(this.manager);return a.setCrossOrigin(this.crossOrigin),a.setPath(this.path),a.load(t,function(o){r.image=o,r.needsUpdate=!0,e!==void 0&&e(r)},n,s),r}}class vr extends Ne{constructor(t,e=1){super(),this.isLight=!0,this.type="Light",this.color=new Kt(t),this.intensity=e}dispose(){}copy(t,e){return super.copy(t,e),this.color.copy(t.color),this.intensity=t.intensity,this}toJSON(t){const e=super.toJSON(t);return e.object.color=this.color.getHex(),e.object.intensity=this.intensity,this.groundColor!==void 0&&(e.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(e.object.distance=this.distance),this.angle!==void 0&&(e.object.angle=this.angle),this.decay!==void 0&&(e.object.decay=this.decay),this.penumbra!==void 0&&(e.object.penumbra=this.penumbra),this.shadow!==void 0&&(e.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(e.object.target=this.target.uuid),e}}class fv extends vr{constructor(t,e,n){super(t,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(Ne.DEFAULT_UP),this.updateMatrix(),this.groundColor=new Kt(e)}copy(t,e){return super.copy(t,e),this.groundColor.copy(t.groundColor),this}}const Da=new jt,wh=new L,Th=new L;class Zc{constructor(t){this.camera=t,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new At(512,512),this.map=null,this.mapPass=null,this.matrix=new jt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Wc,this._frameExtents=new At(1,1),this._viewportCount=1,this._viewports=[new xe(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(t){const e=this.camera,n=this.matrix;wh.setFromMatrixPosition(t.matrixWorld),e.position.copy(wh),Th.setFromMatrixPosition(t.target.matrixWorld),e.lookAt(Th),e.updateMatrixWorld(),Da.multiplyMatrices(e.projectionMatrix,e.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Da),n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(Da)}getViewport(t){return this._viewports[t]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(t){return this.camera=t.camera.clone(),this.intensity=t.intensity,this.bias=t.bias,this.radius=t.radius,this.mapSize.copy(t.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){const t={};return this.intensity!==1&&(t.intensity=this.intensity),this.bias!==0&&(t.bias=this.bias),this.normalBias!==0&&(t.normalBias=this.normalBias),this.radius!==1&&(t.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(t.mapSize=this.mapSize.toArray()),t.camera=this.camera.toJSON(!1).object,delete t.camera.matrix,t}}class pv extends Zc{constructor(){super(new Je(50,1,.5,500)),this.isSpotLightShadow=!0,this.focus=1}updateMatrices(t){const e=this.camera,n=Ps*2*t.angle*this.focus,s=this.mapSize.width/this.mapSize.height,r=t.distance||e.far;(n!==e.fov||s!==e.aspect||r!==e.far)&&(e.fov=n,e.aspect=s,e.far=r,e.updateProjectionMatrix()),super.updateMatrices(t)}copy(t){return super.copy(t),this.focus=t.focus,this}}class mv extends vr{constructor(t,e,n=0,s=Math.PI/3,r=0,a=2){super(t,e),this.isSpotLight=!0,this.type="SpotLight",this.position.copy(Ne.DEFAULT_UP),this.updateMatrix(),this.target=new Ne,this.distance=n,this.angle=s,this.penumbra=r,this.decay=a,this.map=null,this.shadow=new pv}get power(){return this.intensity*Math.PI}set power(t){this.intensity=t/Math.PI}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.angle=t.angle,this.penumbra=t.penumbra,this.decay=t.decay,this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}}const Ah=new jt,Js=new L,Ia=new L;class gv extends Zc{constructor(){super(new Je(90,1,.5,500)),this.isPointLightShadow=!0,this._frameExtents=new At(4,2),this._viewportCount=6,this._viewports=[new xe(2,1,1,1),new xe(0,1,1,1),new xe(3,1,1,1),new xe(1,1,1,1),new xe(3,0,1,1),new xe(1,0,1,1)],this._cubeDirections=[new L(1,0,0),new L(-1,0,0),new L(0,0,1),new L(0,0,-1),new L(0,1,0),new L(0,-1,0)],this._cubeUps=[new L(0,1,0),new L(0,1,0),new L(0,1,0),new L(0,1,0),new L(0,0,1),new L(0,0,-1)]}updateMatrices(t,e=0){const n=this.camera,s=this.matrix,r=t.distance||n.far;r!==n.far&&(n.far=r,n.updateProjectionMatrix()),Js.setFromMatrixPosition(t.matrixWorld),n.position.copy(Js),Ia.copy(n.position),Ia.add(this._cubeDirections[e]),n.up.copy(this._cubeUps[e]),n.lookAt(Ia),n.updateMatrixWorld(),s.makeTranslation(-Js.x,-Js.y,-Js.z),Ah.multiplyMatrices(n.projectionMatrix,n.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Ah)}}class _v extends vr{constructor(t,e,n=0,s=2){super(t,e),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=s,this.shadow=new gv}get power(){return this.intensity*4*Math.PI}set power(t){this.intensity=t/(4*Math.PI)}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.decay=t.decay,this.shadow=t.shadow.clone(),this}}class vv extends Zc{constructor(){super(new Xc(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}}class Uu extends vr{constructor(t,e){super(t,e),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Ne.DEFAULT_UP),this.updateMatrix(),this.target=new Ne,this.shadow=new vv}dispose(){this.shadow.dispose()}copy(t){return super.copy(t),this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}}class xv extends vr{constructor(t,e){super(t,e),this.isAmbientLight=!0,this.type="AmbientLight"}}class Fu{static decodeText(t){if(console.warn("THREE.LoaderUtils: decodeText() has been deprecated with r165 and will be removed with r175. Use TextDecoder instead."),typeof TextDecoder<"u")return new TextDecoder().decode(t);let e="";for(let n=0,s=t.length;n<s;n++)e+=String.fromCharCode(t[n]);try{return decodeURIComponent(escape(e))}catch{return e}}static extractUrlBase(t){const e=t.lastIndexOf("/");return e===-1?"./":t.slice(0,e+1)}static resolveURL(t,e){return typeof t!="string"||t===""?"":(/^https?:\/\//i.test(e)&&/^\//.test(t)&&(e=e.replace(/(^https?:\/\/[^\/]+).*/i,"$1")),/^(https?:)?\/\//i.test(t)||/^data:.*,.*$/i.test(t)||/^blob:.*$/i.test(t)?t:e+t)}}const Ch=new jt;class yv{constructor(t,e,n=0,s=1/0){this.ray=new Fs(t,e),this.near=n,this.far=s,this.camera=null,this.layers=new Gc,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(t,e){this.ray.set(t,e)}setFromCamera(t,e){e.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(e.matrixWorld),this.ray.direction.set(t.x,t.y,.5).unproject(e).sub(this.ray.origin).normalize(),this.camera=e):e.isOrthographicCamera?(this.ray.origin.set(t.x,t.y,(e.near+e.far)/(e.near-e.far)).unproject(e),this.ray.direction.set(0,0,-1).transformDirection(e.matrixWorld),this.camera=e):console.error("THREE.Raycaster: Unsupported camera type: "+e.type)}setFromXRController(t){return Ch.identity().extractRotation(t.matrixWorld),this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(Ch),this}intersectObject(t,e=!0,n=[]){return Rc(t,this,n,e),n.sort(Rh),n}intersectObjects(t,e=!0,n=[]){for(let s=0,r=t.length;s<r;s++)Rc(t[s],this,n,e);return n.sort(Rh),n}}function Rh(i,t){return i.distance-t.distance}function Rc(i,t,e,n){let s=!0;if(i.layers.test(t.layers)&&i.raycast(t,e)===!1&&(s=!1),s===!0&&n===!0){const r=i.children;for(let a=0,o=r.length;a<o;a++)Rc(r[a],t,e,!0)}}class Ph{constructor(t=1,e=0,n=0){return this.radius=t,this.phi=e,this.theta=n,this}set(t,e,n){return this.radius=t,this.phi=e,this.theta=n,this}copy(t){return this.radius=t.radius,this.phi=t.phi,this.theta=t.theta,this}makeSafe(){return this.phi=Math.max(1e-6,Math.min(Math.PI-1e-6,this.phi)),this}setFromVector3(t){return this.setFromCartesianCoords(t.x,t.y,t.z)}setFromCartesianCoords(t,e,n){return this.radius=Math.sqrt(t*t+e*e+n*n),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(t,n),this.phi=Math.acos(qe(e/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}}class Mv extends bo{constructor(t=10,e=10,n=4473924,s=8947848){n=new Kt(n),s=new Kt(s);const r=e/2,a=t/e,o=t/2,c=[],l=[];for(let f=0,p=0,g=-o;f<=e;f++,g+=a){c.push(-o,0,g,o,0,g),c.push(g,0,-o,g,0,o);const _=f===r?n:s;_.toArray(l,p),p+=3,_.toArray(l,p),p+=3,_.toArray(l,p),p+=3,_.toArray(l,p),p+=3}const h=new Pe;h.setAttribute("position",new ne(c,3)),h.setAttribute("color",new ne(l,3));const u=new Bn({vertexColors:!0,toneMapped:!1});super(h,u),this.type="GridHelper"}dispose(){this.geometry.dispose(),this.material.dispose()}}const Lh=new L;let io,Ua;class ji extends Ne{constructor(t=new L(0,0,1),e=new L(0,0,0),n=1,s=16776960,r=n*.2,a=r*.2){super(),this.type="ArrowHelper",io===void 0&&(io=new Pe,io.setAttribute("position",new ne([0,0,0,0,1,0],3)),Ua=new zs(0,.5,1,5,1),Ua.translate(0,-.5,0)),this.position.copy(e),this.line=new Bs(io,new Bn({color:s,toneMapped:!1})),this.line.matrixAutoUpdate=!1,this.add(this.line),this.cone=new me(Ua,new je({color:s,toneMapped:!1})),this.cone.matrixAutoUpdate=!1,this.add(this.cone),this.setDirection(t),this.setLength(n,r,a)}setDirection(t){if(t.y>.99999)this.quaternion.set(0,0,0,1);else if(t.y<-.99999)this.quaternion.set(1,0,0,0);else{Lh.set(t.z,0,-t.x).normalize();const e=Math.acos(t.y);this.quaternion.setFromAxisAngle(Lh,e)}}setLength(t,e=t*.2,n=e*.2){this.line.scale.set(1,Math.max(1e-4,t-e),1),this.line.updateMatrix(),this.cone.scale.set(n,e,n),this.cone.position.y=t,this.cone.updateMatrix()}setColor(t){this.line.material.color.set(t),this.cone.material.color.set(t)}copy(t){return super.copy(t,!1),this.line.copy(t.line),this.cone.copy(t.cone),this}dispose(){this.line.geometry.dispose(),this.line.material.dispose(),this.cone.geometry.dispose(),this.cone.material.dispose()}}class Sv extends $i{constructor(t,e=null){super(),this.object=t,this.domElement=e,this.enabled=!0,this.state=-1,this.keys={},this.mouseButtons={LEFT:null,MIDDLE:null,RIGHT:null},this.touches={ONE:null,TWO:null}}connect(){}disconnect(){}dispose(){}update(){}}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:Uc}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__=Uc);const Nh={type:"change"},Qc={type:"start"},Ou={type:"end"},so=new Fs,Dh=new ii,bv=Math.cos(70*ps.DEG2RAD),Ve=new L,hn=2*Math.PI,we={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},Fa=1e-6;class Ev extends Sv{constructor(t,e=null){super(t,e),this.state=we.NONE,this.enabled=!0,this.target=new L,this.cursor=new L,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:_s.ROTATE,MIDDLE:_s.DOLLY,RIGHT:_s.PAN},this.touches={ONE:ms.ROTATE,TWO:ms.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this._lastPosition=new L,this._lastQuaternion=new Vn,this._lastTargetPosition=new L,this._quat=new Vn().setFromUnitVectors(t.up,new L(0,1,0)),this._quatInverse=this._quat.clone().invert(),this._spherical=new Ph,this._sphericalDelta=new Ph,this._scale=1,this._panOffset=new L,this._rotateStart=new At,this._rotateEnd=new At,this._rotateDelta=new At,this._panStart=new At,this._panEnd=new At,this._panDelta=new At,this._dollyStart=new At,this._dollyEnd=new At,this._dollyDelta=new At,this._dollyDirection=new L,this._mouse=new At,this._performCursorZoom=!1,this._pointers=[],this._pointerPositions={},this._controlActive=!1,this._onPointerMove=Tv.bind(this),this._onPointerDown=wv.bind(this),this._onPointerUp=Av.bind(this),this._onContextMenu=Iv.bind(this),this._onMouseWheel=Pv.bind(this),this._onKeyDown=Lv.bind(this),this._onTouchStart=Nv.bind(this),this._onTouchMove=Dv.bind(this),this._onMouseDown=Cv.bind(this),this._onMouseMove=Rv.bind(this),this._interceptControlDown=Uv.bind(this),this._interceptControlUp=Fv.bind(this),this.domElement!==null&&this.connect(),this.update()}connect(){this.domElement.addEventListener("pointerdown",this._onPointerDown),this.domElement.addEventListener("pointercancel",this._onPointerUp),this.domElement.addEventListener("contextmenu",this._onContextMenu),this.domElement.addEventListener("wheel",this._onMouseWheel,{passive:!1}),this.domElement.getRootNode().addEventListener("keydown",this._interceptControlDown,{passive:!0,capture:!0}),this.domElement.style.touchAction="none"}disconnect(){this.domElement.removeEventListener("pointerdown",this._onPointerDown),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.domElement.removeEventListener("pointercancel",this._onPointerUp),this.domElement.removeEventListener("wheel",this._onMouseWheel),this.domElement.removeEventListener("contextmenu",this._onContextMenu),this.stopListenToKeyEvents(),this.domElement.getRootNode().removeEventListener("keydown",this._interceptControlDown,{capture:!0}),this.domElement.style.touchAction="auto"}dispose(){this.disconnect()}getPolarAngle(){return this._spherical.phi}getAzimuthalAngle(){return this._spherical.theta}getDistance(){return this.object.position.distanceTo(this.target)}listenToKeyEvents(t){t.addEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=t}stopListenToKeyEvents(){this._domElementKeyEvents!==null&&(this._domElementKeyEvents.removeEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=null)}saveState(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom}reset(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent(Nh),this.update(),this.state=we.NONE}update(t=null){const e=this.object.position;Ve.copy(e).sub(this.target),Ve.applyQuaternion(this._quat),this._spherical.setFromVector3(Ve),this.autoRotate&&this.state===we.NONE&&this._rotateLeft(this._getAutoRotationAngle(t)),this.enableDamping?(this._spherical.theta+=this._sphericalDelta.theta*this.dampingFactor,this._spherical.phi+=this._sphericalDelta.phi*this.dampingFactor):(this._spherical.theta+=this._sphericalDelta.theta,this._spherical.phi+=this._sphericalDelta.phi);let n=this.minAzimuthAngle,s=this.maxAzimuthAngle;isFinite(n)&&isFinite(s)&&(n<-Math.PI?n+=hn:n>Math.PI&&(n-=hn),s<-Math.PI?s+=hn:s>Math.PI&&(s-=hn),n<=s?this._spherical.theta=Math.max(n,Math.min(s,this._spherical.theta)):this._spherical.theta=this._spherical.theta>(n+s)/2?Math.max(n,this._spherical.theta):Math.min(s,this._spherical.theta)),this._spherical.phi=Math.max(this.minPolarAngle,Math.min(this.maxPolarAngle,this._spherical.phi)),this._spherical.makeSafe(),this.enableDamping===!0?this.target.addScaledVector(this._panOffset,this.dampingFactor):this.target.add(this._panOffset),this.target.sub(this.cursor),this.target.clampLength(this.minTargetRadius,this.maxTargetRadius),this.target.add(this.cursor);let r=!1;if(this.zoomToCursor&&this._performCursorZoom||this.object.isOrthographicCamera)this._spherical.radius=this._clampDistance(this._spherical.radius);else{const a=this._spherical.radius;this._spherical.radius=this._clampDistance(this._spherical.radius*this._scale),r=a!=this._spherical.radius}if(Ve.setFromSpherical(this._spherical),Ve.applyQuaternion(this._quatInverse),e.copy(this.target).add(Ve),this.object.lookAt(this.target),this.enableDamping===!0?(this._sphericalDelta.theta*=1-this.dampingFactor,this._sphericalDelta.phi*=1-this.dampingFactor,this._panOffset.multiplyScalar(1-this.dampingFactor)):(this._sphericalDelta.set(0,0,0),this._panOffset.set(0,0,0)),this.zoomToCursor&&this._performCursorZoom){let a=null;if(this.object.isPerspectiveCamera){const o=Ve.length();a=this._clampDistance(o*this._scale);const c=o-a;this.object.position.addScaledVector(this._dollyDirection,c),this.object.updateMatrixWorld(),r=!!c}else if(this.object.isOrthographicCamera){const o=new L(this._mouse.x,this._mouse.y,0);o.unproject(this.object);const c=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),this.object.updateProjectionMatrix(),r=c!==this.object.zoom;const l=new L(this._mouse.x,this._mouse.y,0);l.unproject(this.object),this.object.position.sub(l).add(o),this.object.updateMatrixWorld(),a=Ve.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),this.zoomToCursor=!1;a!==null&&(this.screenSpacePanning?this.target.set(0,0,-1).transformDirection(this.object.matrix).multiplyScalar(a).add(this.object.position):(so.origin.copy(this.object.position),so.direction.set(0,0,-1).transformDirection(this.object.matrix),Math.abs(this.object.up.dot(so.direction))<bv?this.object.lookAt(this.target):(Dh.setFromNormalAndCoplanarPoint(this.object.up,this.target),so.intersectPlane(Dh,this.target))))}else if(this.object.isOrthographicCamera){const a=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),a!==this.object.zoom&&(this.object.updateProjectionMatrix(),r=!0)}return this._scale=1,this._performCursorZoom=!1,r||this._lastPosition.distanceToSquared(this.object.position)>Fa||8*(1-this._lastQuaternion.dot(this.object.quaternion))>Fa||this._lastTargetPosition.distanceToSquared(this.target)>Fa?(this.dispatchEvent(Nh),this._lastPosition.copy(this.object.position),this._lastQuaternion.copy(this.object.quaternion),this._lastTargetPosition.copy(this.target),!0):!1}_getAutoRotationAngle(t){return t!==null?hn/60*this.autoRotateSpeed*t:hn/60/60*this.autoRotateSpeed}_getZoomScale(t){const e=Math.abs(t*.01);return Math.pow(.95,this.zoomSpeed*e)}_rotateLeft(t){this._sphericalDelta.theta-=t}_rotateUp(t){this._sphericalDelta.phi-=t}_panLeft(t,e){Ve.setFromMatrixColumn(e,0),Ve.multiplyScalar(-t),this._panOffset.add(Ve)}_panUp(t,e){this.screenSpacePanning===!0?Ve.setFromMatrixColumn(e,1):(Ve.setFromMatrixColumn(e,0),Ve.crossVectors(this.object.up,Ve)),Ve.multiplyScalar(t),this._panOffset.add(Ve)}_pan(t,e){const n=this.domElement;if(this.object.isPerspectiveCamera){const s=this.object.position;Ve.copy(s).sub(this.target);let r=Ve.length();r*=Math.tan(this.object.fov/2*Math.PI/180),this._panLeft(2*t*r/n.clientHeight,this.object.matrix),this._panUp(2*e*r/n.clientHeight,this.object.matrix)}else this.object.isOrthographicCamera?(this._panLeft(t*(this.object.right-this.object.left)/this.object.zoom/n.clientWidth,this.object.matrix),this._panUp(e*(this.object.top-this.object.bottom)/this.object.zoom/n.clientHeight,this.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),this.enablePan=!1)}_dollyOut(t){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale/=t:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_dollyIn(t){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale*=t:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_updateZoomParameters(t,e){if(!this.zoomToCursor)return;this._performCursorZoom=!0;const n=this.domElement.getBoundingClientRect(),s=t-n.left,r=e-n.top,a=n.width,o=n.height;this._mouse.x=s/a*2-1,this._mouse.y=-(r/o)*2+1,this._dollyDirection.set(this._mouse.x,this._mouse.y,1).unproject(this.object).sub(this.object.position).normalize()}_clampDistance(t){return Math.max(this.minDistance,Math.min(this.maxDistance,t))}_handleMouseDownRotate(t){this._rotateStart.set(t.clientX,t.clientY)}_handleMouseDownDolly(t){this._updateZoomParameters(t.clientX,t.clientX),this._dollyStart.set(t.clientX,t.clientY)}_handleMouseDownPan(t){this._panStart.set(t.clientX,t.clientY)}_handleMouseMoveRotate(t){this._rotateEnd.set(t.clientX,t.clientY),this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const e=this.domElement;this._rotateLeft(hn*this._rotateDelta.x/e.clientHeight),this._rotateUp(hn*this._rotateDelta.y/e.clientHeight),this._rotateStart.copy(this._rotateEnd),this.update()}_handleMouseMoveDolly(t){this._dollyEnd.set(t.clientX,t.clientY),this._dollyDelta.subVectors(this._dollyEnd,this._dollyStart),this._dollyDelta.y>0?this._dollyOut(this._getZoomScale(this._dollyDelta.y)):this._dollyDelta.y<0&&this._dollyIn(this._getZoomScale(this._dollyDelta.y)),this._dollyStart.copy(this._dollyEnd),this.update()}_handleMouseMovePan(t){this._panEnd.set(t.clientX,t.clientY),this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd),this.update()}_handleMouseWheel(t){this._updateZoomParameters(t.clientX,t.clientY),t.deltaY<0?this._dollyIn(this._getZoomScale(t.deltaY)):t.deltaY>0&&this._dollyOut(this._getZoomScale(t.deltaY)),this.update()}_handleKeyDown(t){let e=!1;switch(t.code){case this.keys.UP:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateUp(hn*this.rotateSpeed/this.domElement.clientHeight):this._pan(0,this.keyPanSpeed),e=!0;break;case this.keys.BOTTOM:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateUp(-hn*this.rotateSpeed/this.domElement.clientHeight):this._pan(0,-this.keyPanSpeed),e=!0;break;case this.keys.LEFT:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateLeft(hn*this.rotateSpeed/this.domElement.clientHeight):this._pan(this.keyPanSpeed,0),e=!0;break;case this.keys.RIGHT:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateLeft(-hn*this.rotateSpeed/this.domElement.clientHeight):this._pan(-this.keyPanSpeed,0),e=!0;break}e&&(t.preventDefault(),this.update())}_handleTouchStartRotate(t){if(this._pointers.length===1)this._rotateStart.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._rotateStart.set(n,s)}}_handleTouchStartPan(t){if(this._pointers.length===1)this._panStart.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._panStart.set(n,s)}}_handleTouchStartDolly(t){const e=this._getSecondPointerPosition(t),n=t.pageX-e.x,s=t.pageY-e.y,r=Math.sqrt(n*n+s*s);this._dollyStart.set(0,r)}_handleTouchStartDollyPan(t){this.enableZoom&&this._handleTouchStartDolly(t),this.enablePan&&this._handleTouchStartPan(t)}_handleTouchStartDollyRotate(t){this.enableZoom&&this._handleTouchStartDolly(t),this.enableRotate&&this._handleTouchStartRotate(t)}_handleTouchMoveRotate(t){if(this._pointers.length==1)this._rotateEnd.set(t.pageX,t.pageY);else{const n=this._getSecondPointerPosition(t),s=.5*(t.pageX+n.x),r=.5*(t.pageY+n.y);this._rotateEnd.set(s,r)}this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const e=this.domElement;this._rotateLeft(hn*this._rotateDelta.x/e.clientHeight),this._rotateUp(hn*this._rotateDelta.y/e.clientHeight),this._rotateStart.copy(this._rotateEnd)}_handleTouchMovePan(t){if(this._pointers.length===1)this._panEnd.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._panEnd.set(n,s)}this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd)}_handleTouchMoveDolly(t){const e=this._getSecondPointerPosition(t),n=t.pageX-e.x,s=t.pageY-e.y,r=Math.sqrt(n*n+s*s);this._dollyEnd.set(0,r),this._dollyDelta.set(0,Math.pow(this._dollyEnd.y/this._dollyStart.y,this.zoomSpeed)),this._dollyOut(this._dollyDelta.y),this._dollyStart.copy(this._dollyEnd);const a=(t.pageX+e.x)*.5,o=(t.pageY+e.y)*.5;this._updateZoomParameters(a,o)}_handleTouchMoveDollyPan(t){this.enableZoom&&this._handleTouchMoveDolly(t),this.enablePan&&this._handleTouchMovePan(t)}_handleTouchMoveDollyRotate(t){this.enableZoom&&this._handleTouchMoveDolly(t),this.enableRotate&&this._handleTouchMoveRotate(t)}_addPointer(t){this._pointers.push(t.pointerId)}_removePointer(t){delete this._pointerPositions[t.pointerId];for(let e=0;e<this._pointers.length;e++)if(this._pointers[e]==t.pointerId){this._pointers.splice(e,1);return}}_isTrackingPointer(t){for(let e=0;e<this._pointers.length;e++)if(this._pointers[e]==t.pointerId)return!0;return!1}_trackPointer(t){let e=this._pointerPositions[t.pointerId];e===void 0&&(e=new At,this._pointerPositions[t.pointerId]=e),e.set(t.pageX,t.pageY)}_getSecondPointerPosition(t){const e=t.pointerId===this._pointers[0]?this._pointers[1]:this._pointers[0];return this._pointerPositions[e]}_customWheelEvent(t){const e=t.deltaMode,n={clientX:t.clientX,clientY:t.clientY,deltaY:t.deltaY};switch(e){case 1:n.deltaY*=16;break;case 2:n.deltaY*=100;break}return t.ctrlKey&&!this._controlActive&&(n.deltaY*=10),n}}function wv(i){this.enabled!==!1&&(this._pointers.length===0&&(this.domElement.setPointerCapture(i.pointerId),this.domElement.addEventListener("pointermove",this._onPointerMove),this.domElement.addEventListener("pointerup",this._onPointerUp)),!this._isTrackingPointer(i)&&(this._addPointer(i),i.pointerType==="touch"?this._onTouchStart(i):this._onMouseDown(i)))}function Tv(i){this.enabled!==!1&&(i.pointerType==="touch"?this._onTouchMove(i):this._onMouseMove(i))}function Av(i){switch(this._removePointer(i),this._pointers.length){case 0:this.domElement.releasePointerCapture(i.pointerId),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.dispatchEvent(Ou),this.state=we.NONE;break;case 1:const t=this._pointers[0],e=this._pointerPositions[t];this._onTouchStart({pointerId:t,pageX:e.x,pageY:e.y});break}}function Cv(i){let t;switch(i.button){case 0:t=this.mouseButtons.LEFT;break;case 1:t=this.mouseButtons.MIDDLE;break;case 2:t=this.mouseButtons.RIGHT;break;default:t=-1}switch(t){case _s.DOLLY:if(this.enableZoom===!1)return;this._handleMouseDownDolly(i),this.state=we.DOLLY;break;case _s.ROTATE:if(i.ctrlKey||i.metaKey||i.shiftKey){if(this.enablePan===!1)return;this._handleMouseDownPan(i),this.state=we.PAN}else{if(this.enableRotate===!1)return;this._handleMouseDownRotate(i),this.state=we.ROTATE}break;case _s.PAN:if(i.ctrlKey||i.metaKey||i.shiftKey){if(this.enableRotate===!1)return;this._handleMouseDownRotate(i),this.state=we.ROTATE}else{if(this.enablePan===!1)return;this._handleMouseDownPan(i),this.state=we.PAN}break;default:this.state=we.NONE}this.state!==we.NONE&&this.dispatchEvent(Qc)}function Rv(i){switch(this.state){case we.ROTATE:if(this.enableRotate===!1)return;this._handleMouseMoveRotate(i);break;case we.DOLLY:if(this.enableZoom===!1)return;this._handleMouseMoveDolly(i);break;case we.PAN:if(this.enablePan===!1)return;this._handleMouseMovePan(i);break}}function Pv(i){this.enabled===!1||this.enableZoom===!1||this.state!==we.NONE||(i.preventDefault(),this.dispatchEvent(Qc),this._handleMouseWheel(this._customWheelEvent(i)),this.dispatchEvent(Ou))}function Lv(i){this.enabled===!1||this.enablePan===!1||this._handleKeyDown(i)}function Nv(i){switch(this._trackPointer(i),this._pointers.length){case 1:switch(this.touches.ONE){case ms.ROTATE:if(this.enableRotate===!1)return;this._handleTouchStartRotate(i),this.state=we.TOUCH_ROTATE;break;case ms.PAN:if(this.enablePan===!1)return;this._handleTouchStartPan(i),this.state=we.TOUCH_PAN;break;default:this.state=we.NONE}break;case 2:switch(this.touches.TWO){case ms.DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchStartDollyPan(i),this.state=we.TOUCH_DOLLY_PAN;break;case ms.DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchStartDollyRotate(i),this.state=we.TOUCH_DOLLY_ROTATE;break;default:this.state=we.NONE}break;default:this.state=we.NONE}this.state!==we.NONE&&this.dispatchEvent(Qc)}function Dv(i){switch(this._trackPointer(i),this.state){case we.TOUCH_ROTATE:if(this.enableRotate===!1)return;this._handleTouchMoveRotate(i),this.update();break;case we.TOUCH_PAN:if(this.enablePan===!1)return;this._handleTouchMovePan(i),this.update();break;case we.TOUCH_DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchMoveDollyPan(i),this.update();break;case we.TOUCH_DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchMoveDollyRotate(i),this.update();break;default:this.state=we.NONE}}function Iv(i){this.enabled!==!1&&i.preventDefault()}function Uv(i){i.key==="Control"&&(this._controlActive=!0,this.domElement.getRootNode().addEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function Fv(i){i.key==="Control"&&(this._controlActive=!1,this.domElement.getRootNode().removeEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}const Ov=/^[og]\s*(.+)?/,kv=/^mtllib /,Bv=/^usemtl /,zv=/^usemap /,Ih=/\s+/,Uh=new L,Oa=new L,Fh=new L,Oh=new L,En=new L,ro=new Kt;function Vv(){const i={objects:[],object:{},vertices:[],normals:[],colors:[],uvs:[],materials:{},materialLibraries:[],startObject:function(t,e){if(this.object&&this.object.fromDeclaration===!1){this.object.name=t,this.object.fromDeclaration=e!==!1;return}const n=this.object&&typeof this.object.currentMaterial=="function"?this.object.currentMaterial():void 0;if(this.object&&typeof this.object._finalize=="function"&&this.object._finalize(!0),this.object={name:t||"",fromDeclaration:e!==!1,geometry:{vertices:[],normals:[],colors:[],uvs:[],hasUVIndices:!1},materials:[],smooth:!0,startMaterial:function(s,r){const a=this._finalize(!1);a&&(a.inherited||a.groupCount<=0)&&this.materials.splice(a.index,1);const o={index:this.materials.length,name:s||"",mtllib:Array.isArray(r)&&r.length>0?r[r.length-1]:"",smooth:a!==void 0?a.smooth:this.smooth,groupStart:a!==void 0?a.groupEnd:0,groupEnd:-1,groupCount:-1,inherited:!1,clone:function(c){const l={index:typeof c=="number"?c:this.index,name:this.name,mtllib:this.mtllib,smooth:this.smooth,groupStart:0,groupEnd:-1,groupCount:-1,inherited:!1};return l.clone=this.clone.bind(l),l}};return this.materials.push(o),o},currentMaterial:function(){if(this.materials.length>0)return this.materials[this.materials.length-1]},_finalize:function(s){const r=this.currentMaterial();if(r&&r.groupEnd===-1&&(r.groupEnd=this.geometry.vertices.length/3,r.groupCount=r.groupEnd-r.groupStart,r.inherited=!1),s&&this.materials.length>1)for(let a=this.materials.length-1;a>=0;a--)this.materials[a].groupCount<=0&&this.materials.splice(a,1);return s&&this.materials.length===0&&this.materials.push({name:"",smooth:this.smooth}),r}},n&&n.name&&typeof n.clone=="function"){const s=n.clone(0);s.inherited=!0,this.object.materials.push(s)}this.objects.push(this.object)},finalize:function(){this.object&&typeof this.object._finalize=="function"&&this.object._finalize(!0)},parseVertexIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/3)*3},parseNormalIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/3)*3},parseUVIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/2)*2},addVertex:function(t,e,n){const s=this.vertices,r=this.object.geometry.vertices;r.push(s[t+0],s[t+1],s[t+2]),r.push(s[e+0],s[e+1],s[e+2]),r.push(s[n+0],s[n+1],s[n+2])},addVertexPoint:function(t){const e=this.vertices;this.object.geometry.vertices.push(e[t+0],e[t+1],e[t+2])},addVertexLine:function(t){const e=this.vertices;this.object.geometry.vertices.push(e[t+0],e[t+1],e[t+2])},addNormal:function(t,e,n){const s=this.normals,r=this.object.geometry.normals;r.push(s[t+0],s[t+1],s[t+2]),r.push(s[e+0],s[e+1],s[e+2]),r.push(s[n+0],s[n+1],s[n+2])},addFaceNormal:function(t,e,n){const s=this.vertices,r=this.object.geometry.normals;Uh.fromArray(s,t),Oa.fromArray(s,e),Fh.fromArray(s,n),En.subVectors(Fh,Oa),Oh.subVectors(Uh,Oa),En.cross(Oh),En.normalize(),r.push(En.x,En.y,En.z),r.push(En.x,En.y,En.z),r.push(En.x,En.y,En.z)},addColor:function(t,e,n){const s=this.colors,r=this.object.geometry.colors;s[t]!==void 0&&r.push(s[t+0],s[t+1],s[t+2]),s[e]!==void 0&&r.push(s[e+0],s[e+1],s[e+2]),s[n]!==void 0&&r.push(s[n+0],s[n+1],s[n+2])},addUV:function(t,e,n){const s=this.uvs,r=this.object.geometry.uvs;r.push(s[t+0],s[t+1]),r.push(s[e+0],s[e+1]),r.push(s[n+0],s[n+1])},addDefaultUV:function(){const t=this.object.geometry.uvs;t.push(0,0),t.push(0,0),t.push(0,0)},addUVLine:function(t){const e=this.uvs;this.object.geometry.uvs.push(e[t+0],e[t+1])},addFace:function(t,e,n,s,r,a,o,c,l){const h=this.vertices.length;let u=this.parseVertexIndex(t,h),f=this.parseVertexIndex(e,h),p=this.parseVertexIndex(n,h);if(this.addVertex(u,f,p),this.addColor(u,f,p),o!==void 0&&o!==""){const g=this.normals.length;u=this.parseNormalIndex(o,g),f=this.parseNormalIndex(c,g),p=this.parseNormalIndex(l,g),this.addNormal(u,f,p)}else this.addFaceNormal(u,f,p);if(s!==void 0&&s!==""){const g=this.uvs.length;u=this.parseUVIndex(s,g),f=this.parseUVIndex(r,g),p=this.parseUVIndex(a,g),this.addUV(u,f,p),this.object.geometry.hasUVIndices=!0}else this.addDefaultUV()},addPointGeometry:function(t){this.object.geometry.type="Points";const e=this.vertices.length;for(let n=0,s=t.length;n<s;n++){const r=this.parseVertexIndex(t[n],e);this.addVertexPoint(r),this.addColor(r)}},addLineGeometry:function(t,e){this.object.geometry.type="Line";const n=this.vertices.length,s=this.uvs.length;for(let r=0,a=t.length;r<a;r++)this.addVertexLine(this.parseVertexIndex(t[r],n));for(let r=0,a=e.length;r<a;r++)this.addUVLine(this.parseUVIndex(e[r],s))}};return i.startObject("",!1),i}class kh extends hi{constructor(t){super(t),this.materials=null}load(t,e,n,s){const r=this,a=new Ho(this.manager);a.setPath(this.path),a.setRequestHeader(this.requestHeader),a.setWithCredentials(this.withCredentials),a.load(t,function(o){try{e(r.parse(o))}catch(c){s?s(c):console.error(c),r.manager.itemError(t)}},n,s)}setMaterials(t){return this.materials=t,this}parse(t){const e=new Vv;t.indexOf(`\r
`)!==-1&&(t=t.replace(/\r\n/g,`
`)),t.indexOf(`\\
`)!==-1&&(t=t.replace(/\\\n/g,""));const n=t.split(`
`);let s=[];for(let o=0,c=n.length;o<c;o++){const l=n[o].trimStart();if(l.length===0)continue;const h=l.charAt(0);if(h!=="#")if(h==="v"){const u=l.split(Ih);switch(u[0]){case"v":e.vertices.push(parseFloat(u[1]),parseFloat(u[2]),parseFloat(u[3])),u.length>=7?(ro.setRGB(parseFloat(u[4]),parseFloat(u[5]),parseFloat(u[6]),Le),e.colors.push(ro.r,ro.g,ro.b)):e.colors.push(void 0,void 0,void 0);break;case"vn":e.normals.push(parseFloat(u[1]),parseFloat(u[2]),parseFloat(u[3]));break;case"vt":e.uvs.push(parseFloat(u[1]),parseFloat(u[2]));break}}else if(h==="f"){const f=l.slice(1).trim().split(Ih),p=[];for(let _=0,m=f.length;_<m;_++){const d=f[_];if(d.length>0){const w=d.split("/");p.push(w)}}const g=p[0];for(let _=1,m=p.length-1;_<m;_++){const d=p[_],w=p[_+1];e.addFace(g[0],d[0],w[0],g[1],d[1],w[1],g[2],d[2],w[2])}}else if(h==="l"){const u=l.substring(1).trim().split(" ");let f=[];const p=[];if(l.indexOf("/")===-1)f=u;else for(let g=0,_=u.length;g<_;g++){const m=u[g].split("/");m[0]!==""&&f.push(m[0]),m[1]!==""&&p.push(m[1])}e.addLineGeometry(f,p)}else if(h==="p"){const f=l.slice(1).trim().split(" ");e.addPointGeometry(f)}else if((s=Ov.exec(l))!==null){const u=(" "+s[0].slice(1).trim()).slice(1);e.startObject(u)}else if(Bv.test(l))e.object.startMaterial(l.substring(7).trim(),e.materialLibraries);else if(kv.test(l))e.materialLibraries.push(l.substring(7).trim());else if(zv.test(l))console.warn('THREE.OBJLoader: Rendering identifier "usemap" not supported. Textures must be defined in MTL files.');else if(h==="s"){if(s=l.split(" "),s.length>1){const f=s[1].trim().toLowerCase();e.object.smooth=f!=="0"&&f!=="off"}else e.object.smooth=!0;const u=e.object.currentMaterial();u&&(u.smooth=e.object.smooth)}else{if(l==="\0")continue;console.warn('THREE.OBJLoader: Unexpected line: "'+l+'"')}}e.finalize();const r=new Fe;if(r.materialLibraries=[].concat(e.materialLibraries),!(e.objects.length===1&&e.objects[0].geometry.vertices.length===0)===!0)for(let o=0,c=e.objects.length;o<c;o++){const l=e.objects[o],h=l.geometry,u=l.materials,f=h.type==="Line",p=h.type==="Points";let g=!1;if(h.vertices.length===0)continue;const _=new Pe;_.setAttribute("position",new ne(h.vertices,3)),h.normals.length>0&&_.setAttribute("normal",new ne(h.normals,3)),h.colors.length>0&&(g=!0,_.setAttribute("color",new ne(h.colors,3))),h.hasUVIndices===!0&&_.setAttribute("uv",new ne(h.uvs,2));const m=[];for(let w=0,T=u.length;w<T;w++){const M=u[w],F=M.name+"_"+M.smooth+"_"+g;let P=e.materials[F];if(this.materials!==null){if(P=this.materials.create(M.name),f&&P&&!(P instanceof Bn)){const N=new Bn;Hn.prototype.copy.call(N,P),N.color.copy(P.color),P=N}else if(p&&P&&!(P instanceof tr)){const N=new tr({size:10,sizeAttenuation:!1});Hn.prototype.copy.call(N,P),N.color.copy(P.color),N.map=P.map,P=N}}P===void 0&&(f?P=new Bn:p?P=new tr({size:1,sizeAttenuation:!1}):P=new Ms,P.name=M.name,P.flatShading=!M.smooth,P.vertexColors=g,e.materials[F]=P),m.push(P)}let d;if(m.length>1){for(let w=0,T=u.length;w<T;w++){const M=u[w];_.addGroup(M.groupStart,M.groupCount,w)}f?d=new bo(_,m):p?d=new Ra(_,m):d=new me(_,m)}else f?d=new bo(_,m[0]):p?d=new Ra(_,m[0]):d=new me(_,m[0]);d.name=l.name,r.add(d)}else if(e.vertices.length>0){const o=new tr({size:1,sizeAttenuation:!1}),c=new Pe;c.setAttribute("position",new ne(e.vertices,3)),e.colors.length>0&&e.colors[0]!==void 0&&(c.setAttribute("color",new ne(e.colors,3)),o.vertexColors=!0);const l=new Ra(c,o);r.add(l)}return r}}class Hv extends hi{constructor(t){super(t)}load(t,e,n,s){const r=this,a=new Ho(this.manager);a.setPath(this.path),a.setResponseType("arraybuffer"),a.setRequestHeader(this.requestHeader),a.setWithCredentials(this.withCredentials),a.load(t,function(o){try{e(r.parse(o))}catch(c){s?s(c):console.error(c),r.manager.itemError(t)}},n,s)}parse(t){function e(l){const h=new DataView(l),u=32/8*3+32/8*3*3+16/8,f=h.getUint32(80,!0);if(80+32/8+f*u===h.byteLength)return!0;const g=[115,111,108,105,100];for(let _=0;_<5;_++)if(n(g,h,_))return!1;return!0}function n(l,h,u){for(let f=0,p=l.length;f<p;f++)if(l[f]!==h.getUint8(u+f))return!1;return!0}function s(l){const h=new DataView(l),u=h.getUint32(80,!0);let f,p,g,_=!1,m,d,w,T,M;for(let U=0;U<70;U++)h.getUint32(U,!1)==1129270351&&h.getUint8(U+4)==82&&h.getUint8(U+5)==61&&(_=!0,m=new Float32Array(u*3*3),d=h.getUint8(U+6)/255,w=h.getUint8(U+7)/255,T=h.getUint8(U+8)/255,M=h.getUint8(U+9)/255);const F=84,P=50,N=new Pe,D=new Float32Array(u*3*3),y=new Float32Array(u*3*3),S=new Kt;for(let U=0;U<u;U++){const k=F+U*P,H=h.getFloat32(k,!0),J=h.getFloat32(k+4,!0),Q=h.getFloat32(k+8,!0);if(_){const O=h.getUint16(k+48,!0);(O&32768)===0?(f=(O&31)/31,p=(O>>5&31)/31,g=(O>>10&31)/31):(f=d,p=w,g=T)}for(let O=1;O<=3;O++){const tt=k+O*12,W=U*3*3+(O-1)*3;D[W]=h.getFloat32(tt,!0),D[W+1]=h.getFloat32(tt+4,!0),D[W+2]=h.getFloat32(tt+8,!0),y[W]=H,y[W+1]=J,y[W+2]=Q,_&&(S.setRGB(f,p,g,Le),m[W]=S.r,m[W+1]=S.g,m[W+2]=S.b)}}return N.setAttribute("position",new xn(D,3)),N.setAttribute("normal",new xn(y,3)),_&&(N.setAttribute("color",new xn(m,3)),N.hasColors=!0,N.alpha=M),N}function r(l){const h=new Pe,u=/solid([\s\S]*?)endsolid/g,f=/facet([\s\S]*?)endfacet/g,p=/solid\s(.+)/;let g=0;const _=/[\s]+([+-]?(?:\d*)(?:\.\d*)?(?:[eE][+-]?\d+)?)/.source,m=new RegExp("vertex"+_+_+_,"g"),d=new RegExp("normal"+_+_+_,"g"),w=[],T=[],M=[],F=new L;let P,N=0,D=0,y=0;for(;(P=u.exec(l))!==null;){D=y;const S=P[0],U=(P=p.exec(S))!==null?P[1]:"";for(M.push(U);(P=f.exec(S))!==null;){let J=0,Q=0;const O=P[0];for(;(P=d.exec(O))!==null;)F.x=parseFloat(P[1]),F.y=parseFloat(P[2]),F.z=parseFloat(P[3]),Q++;for(;(P=m.exec(O))!==null;)w.push(parseFloat(P[1]),parseFloat(P[2]),parseFloat(P[3])),T.push(F.x,F.y,F.z),J++,y++;Q!==1&&console.error("THREE.STLLoader: Something isn't right with the normal of face number "+g),J!==3&&console.error("THREE.STLLoader: Something isn't right with the vertices of face number "+g),g++}const k=D,H=y-D;h.userData.groupNames=M,h.addGroup(k,H,N),N++}return h.setAttribute("position",new ne(w,3)),h.setAttribute("normal",new ne(T,3)),h}function a(l){return typeof l!="string"?new TextDecoder().decode(l):l}function o(l){if(typeof l=="string"){const h=new Uint8Array(l.length);for(let u=0;u<l.length;u++)h[u]=l.charCodeAt(u)&255;return h.buffer||h}else return l}const c=o(t);return e(c)?s(c):r(a(t))}}class Bh extends dv{constructor(t){super(t)}parse(t){function e(O){switch(O.image_type){case f:case _:if(O.colormap_length>256||O.colormap_size!==24||O.colormap_type!==1)throw new Error("THREE.TGALoader: Invalid type colormap data for indexed type.");break;case p:case g:case m:case d:if(O.colormap_type)throw new Error("THREE.TGALoader: Invalid type colormap data for colormap type.");break;case u:throw new Error("THREE.TGALoader: No data.");default:throw new Error("THREE.TGALoader: Invalid type "+O.image_type)}if(O.width<=0||O.height<=0)throw new Error("THREE.TGALoader: Invalid image size.");if(O.pixel_size!==8&&O.pixel_size!==16&&O.pixel_size!==24&&O.pixel_size!==32)throw new Error("THREE.TGALoader: Invalid pixel size "+O.pixel_size)}function n(O,tt,W,ct,ft){let pt,Rt;const wt=W.pixel_size>>3,X=W.width*W.height*wt;if(tt&&(Rt=ft.subarray(ct,ct+=W.colormap_length*(W.colormap_size>>3))),O){pt=new Uint8Array(X);let K,nt,it,vt=0;const zt=new Uint8Array(wt);for(;vt<X;)if(K=ft[ct++],nt=(K&127)+1,K&128){for(it=0;it<wt;++it)zt[it]=ft[ct++];for(it=0;it<nt;++it)pt.set(zt,vt+it*wt);vt+=wt*nt}else{for(nt*=wt,it=0;it<nt;++it)pt[vt+it]=ft[ct++];vt+=nt}}else pt=ft.subarray(ct,ct+=tt?W.width*W.height:X);return{pixel_data:pt,palettes:Rt}}function s(O,tt,W,ct,ft,pt,Rt,wt,X){const K=X;let nt,it=0,vt,zt;const Zt=S.width;for(zt=tt;zt!==ct;zt+=W)for(vt=ft;vt!==Rt;vt+=pt,it++)nt=wt[it],O[(vt+Zt*zt)*4+3]=255,O[(vt+Zt*zt)*4+2]=K[nt*3+0],O[(vt+Zt*zt)*4+1]=K[nt*3+1],O[(vt+Zt*zt)*4+0]=K[nt*3+2];return O}function r(O,tt,W,ct,ft,pt,Rt,wt){let X,K=0,nt,it;const vt=S.width;for(it=tt;it!==ct;it+=W)for(nt=ft;nt!==Rt;nt+=pt,K+=2)X=wt[K+0]+(wt[K+1]<<8),O[(nt+vt*it)*4+0]=(X&31744)>>7,O[(nt+vt*it)*4+1]=(X&992)>>2,O[(nt+vt*it)*4+2]=(X&31)<<3,O[(nt+vt*it)*4+3]=X&32768?0:255;return O}function a(O,tt,W,ct,ft,pt,Rt,wt){let X=0,K,nt;const it=S.width;for(nt=tt;nt!==ct;nt+=W)for(K=ft;K!==Rt;K+=pt,X+=3)O[(K+it*nt)*4+3]=255,O[(K+it*nt)*4+2]=wt[X+0],O[(K+it*nt)*4+1]=wt[X+1],O[(K+it*nt)*4+0]=wt[X+2];return O}function o(O,tt,W,ct,ft,pt,Rt,wt){let X=0,K,nt;const it=S.width;for(nt=tt;nt!==ct;nt+=W)for(K=ft;K!==Rt;K+=pt,X+=4)O[(K+it*nt)*4+2]=wt[X+0],O[(K+it*nt)*4+1]=wt[X+1],O[(K+it*nt)*4+0]=wt[X+2],O[(K+it*nt)*4+3]=wt[X+3];return O}function c(O,tt,W,ct,ft,pt,Rt,wt){let X,K=0,nt,it;const vt=S.width;for(it=tt;it!==ct;it+=W)for(nt=ft;nt!==Rt;nt+=pt,K++)X=wt[K],O[(nt+vt*it)*4+0]=X,O[(nt+vt*it)*4+1]=X,O[(nt+vt*it)*4+2]=X,O[(nt+vt*it)*4+3]=255;return O}function l(O,tt,W,ct,ft,pt,Rt,wt){let X=0,K,nt;const it=S.width;for(nt=tt;nt!==ct;nt+=W)for(K=ft;K!==Rt;K+=pt,X+=2)O[(K+it*nt)*4+0]=wt[X+0],O[(K+it*nt)*4+1]=wt[X+0],O[(K+it*nt)*4+2]=wt[X+0],O[(K+it*nt)*4+3]=wt[X+1];return O}function h(O,tt,W,ct,ft){let pt,Rt,wt,X,K,nt;switch((S.flags&w)>>T){default:case P:pt=0,wt=1,K=tt,Rt=0,X=1,nt=W;break;case M:pt=0,wt=1,K=tt,Rt=W-1,X=-1,nt=-1;break;case N:pt=tt-1,wt=-1,K=-1,Rt=0,X=1,nt=W;break;case F:pt=tt-1,wt=-1,K=-1,Rt=W-1,X=-1,nt=-1;break}if(H)switch(S.pixel_size){case 8:c(O,Rt,X,nt,pt,wt,K,ct);break;case 16:l(O,Rt,X,nt,pt,wt,K,ct);break;default:throw new Error("THREE.TGALoader: Format not supported.")}else switch(S.pixel_size){case 8:s(O,Rt,X,nt,pt,wt,K,ct,ft);break;case 16:r(O,Rt,X,nt,pt,wt,K,ct);break;case 24:a(O,Rt,X,nt,pt,wt,K,ct);break;case 32:o(O,Rt,X,nt,pt,wt,K,ct);break;default:throw new Error("THREE.TGALoader: Format not supported.")}return O}const u=0,f=1,p=2,g=3,_=9,m=10,d=11,w=48,T=4,M=0,F=1,P=2,N=3;if(t.length<19)throw new Error("THREE.TGALoader: Not enough data to contain header.");let D=0;const y=new Uint8Array(t),S={id_length:y[D++],colormap_type:y[D++],image_type:y[D++],colormap_index:y[D++]|y[D++]<<8,colormap_length:y[D++]|y[D++]<<8,colormap_size:y[D++],origin:[y[D++]|y[D++]<<8,y[D++]|y[D++]<<8],width:y[D++]|y[D++]<<8,height:y[D++]|y[D++]<<8,pixel_size:y[D++],flags:y[D++]};if(e(S),S.id_length+D>t.length)throw new Error("THREE.TGALoader: No data.");D+=S.id_length;let U=!1,k=!1,H=!1;switch(S.image_type){case _:U=!0,k=!0;break;case f:k=!0;break;case m:U=!0;break;case p:break;case d:U=!0,H=!0;break;case g:H=!0;break}const J=new Uint8Array(S.width*S.height*4),Q=n(U,k,S,D,y);return h(J,S.width,S.height,Q.pixel_data,Q.palettes),{data:J,width:S.width,height:S.height,flipY:!0,generateMipmaps:!0,minFilter:si}}}class Gv extends hi{load(t,e,n,s){const r=this,a=r.path===""?Fu.extractUrlBase(t):r.path,o=new Ho(r.manager);o.setPath(r.path),o.setRequestHeader(r.requestHeader),o.setWithCredentials(r.withCredentials),o.load(t,function(c){try{e(r.parse(c,a))}catch(l){s?s(l):console.error(l),r.manager.itemError(t)}},n,s)}parse(t,e){function n(x,v){const A=[],E=x.childNodes;for(let R=0,$=E.length;R<$;R++){const st=E[R];st.nodeName===v&&A.push(st)}return A}function s(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),A=new Array(v.length);for(let E=0,R=v.length;E<R;E++)A[E]=v[E];return A}function r(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),A=new Array(v.length);for(let E=0,R=v.length;E<R;E++)A[E]=parseFloat(v[E]);return A}function a(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),A=new Array(v.length);for(let E=0,R=v.length;E<R;E++)A[E]=parseInt(v[E]);return A}function o(x){return x.substring(1)}function c(){return"three_default_"+pd++}function l(x){return Object.keys(x).length===0}function h(x){return{unit:u(n(x,"unit")[0]),upAxis:f(n(x,"up_axis")[0])}}function u(x){return x!==void 0&&x.hasAttribute("meter")===!0?parseFloat(x.getAttribute("meter")):1}function f(x){return x!==void 0?x.textContent:"Y_UP"}function p(x,v,A,E){const R=n(x,v)[0];if(R!==void 0){const $=n(R,A);for(let st=0;st<$.length;st++)E($[st])}}function g(x,v){for(const A in x){const E=x[A];E.build=v(x[A])}}function _(x,v){return x.build!==void 0||(x.build=v(x)),x.build}function m(x){const v={sources:{},samplers:{},channels:{}};let A=!1;for(let E=0,R=x.childNodes.length;E<R;E++){const $=x.childNodes[E];if($.nodeType!==1)continue;let st;switch($.nodeName){case"source":st=$.getAttribute("id"),v.sources[st]=Z($);break;case"sampler":st=$.getAttribute("id"),v.samplers[st]=d($);break;case"channel":st=$.getAttribute("target"),v.channels[st]=w($);break;case"animation":m($),A=!0;break;default:console.log($)}}A===!1&&(qt.animations[x.getAttribute("id")||ps.generateUUID()]=v)}function d(x){const v={inputs:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"input":const $=o(R.getAttribute("source")),st=R.getAttribute("semantic");v.inputs[st]=$;break}}return v}function w(x){const v={};let E=x.getAttribute("target").split("/");const R=E.shift();let $=E.shift();const st=$.indexOf("(")!==-1,Tt=$.indexOf(".")!==-1;if(Tt)E=$.split("."),$=E.shift(),v.member=E.shift();else if(st){const mt=$.split("(");$=mt.shift();for(let bt=0;bt<mt.length;bt++)mt[bt]=parseInt(mt[bt].replace(/\)/,""));v.indices=mt}return v.id=R,v.sid=$,v.arraySyntax=st,v.memberSyntax=Tt,v.sampler=o(x.getAttribute("source")),v}function T(x){const v=[],A=x.channels,E=x.samplers,R=x.sources;for(const $ in A)if(A.hasOwnProperty($)){const st=A[$],Tt=E[st.sampler],mt=Tt.inputs.INPUT,bt=Tt.inputs.OUTPUT,Bt=R[mt],ht=R[bt],kt=F(st,Bt,ht);S(kt,v)}return v}function M(x){return _(qt.animations[x],T)}function F(x,v,A){const E=qt.nodes[x.id],R=Oe(E.id),$=E.transforms[x.sid],st=E.matrix.clone().transpose();let Tt,mt,bt,Bt,ht,kt;const Nt={};switch($){case"matrix":for(bt=0,Bt=v.array.length;bt<Bt;bt++)if(Tt=v.array[bt],mt=bt*A.stride,Nt[Tt]===void 0&&(Nt[Tt]={}),x.arraySyntax===!0){const Ie=A.array[mt],Se=x.indices[0]+4*x.indices[1];Nt[Tt][Se]=Ie}else for(ht=0,kt=A.stride;ht<kt;ht++)Nt[Tt][ht]=A.array[mt+ht];break;case"translate":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',$);break;case"rotate":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',$);break;case"scale":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',$);break}const Gt=P(Nt,st);return{name:R.uuid,keyframes:Gt}}function P(x,v){const A=[];for(const R in x)A.push({time:parseFloat(R),value:x[R]});A.sort(E);for(let R=0;R<16;R++)U(A,R,v.elements[R]);return A;function E(R,$){return R.time-$.time}}const N=new L,D=new L,y=new Vn;function S(x,v){const A=x.keyframes,E=x.name,R=[],$=[],st=[],Tt=[];for(let mt=0,bt=A.length;mt<bt;mt++){const Bt=A[mt],ht=Bt.time,kt=Bt.value;B.fromArray(kt).transpose(),B.decompose(N,y,D),R.push(ht),$.push(N.x,N.y,N.z),st.push(y.x,y.y,y.z,y.w),Tt.push(D.x,D.y,D.z)}return $.length>0&&v.push(new Ns(E+".position",R,$)),st.length>0&&v.push(new _r(E+".quaternion",R,st)),Tt.length>0&&v.push(new Ns(E+".scale",R,Tt)),v}function U(x,v,A){let E,R=!0,$,st;for($=0,st=x.length;$<st;$++)E=x[$],E.value[v]===void 0?E.value[v]=null:R=!1;if(R===!0)for($=0,st=x.length;$<st;$++)E=x[$],E.value[v]=A;else k(x,v)}function k(x,v){let A,E;for(let R=0,$=x.length;R<$;R++){const st=x[R];if(st.value[v]===null){if(A=H(x,R,v),E=J(x,R,v),A===null){st.value[v]=E.value[v];continue}if(E===null){st.value[v]=A.value[v];continue}Q(st,A,E,v)}}}function H(x,v,A){for(;v>=0;){const E=x[v];if(E.value[A]!==null)return E;v--}return null}function J(x,v,A){for(;v<x.length;){const E=x[v];if(E.value[A]!==null)return E;v++}return null}function Q(x,v,A,E){if(A.time-v.time===0){x.value[E]=v.value[E];return}x.value[E]=(x.time-v.time)*(A.value[E]-v.value[E])/(A.time-v.time)+v.value[E]}function O(x){const v={name:x.getAttribute("id")||"default",start:parseFloat(x.getAttribute("start")||0),end:parseFloat(x.getAttribute("end")||0),animations:[]};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"instance_animation":v.animations.push(o(R.getAttribute("url")));break}}qt.clips[x.getAttribute("id")]=v}function tt(x){const v=[],A=x.name,E=x.end-x.start||-1,R=x.animations;for(let $=0,st=R.length;$<st;$++){const Tt=M(R[$]);for(let mt=0,bt=Tt.length;mt<bt;mt++)v.push(Tt[mt])}return new Eh(A,E,v)}function W(x){return _(qt.clips[x],tt)}function ct(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"skin":v.id=o(R.getAttribute("source")),v.skin=ft(R);break;case"morph":v.id=o(R.getAttribute("source")),console.warn("THREE.ColladaLoader: Morph target animation not supported yet.");break}}qt.controllers[x.getAttribute("id")]=v}function ft(x){const v={sources:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"bind_shape_matrix":v.bindShapeMatrix=r(R.textContent);break;case"source":const $=R.getAttribute("id");v.sources[$]=Z(R);break;case"joints":v.joints=pt(R);break;case"vertex_weights":v.vertexWeights=Rt(R);break}}return v}function pt(x){const v={inputs:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"input":const $=R.getAttribute("semantic"),st=o(R.getAttribute("source"));v.inputs[$]=st;break}}return v}function Rt(x){const v={inputs:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"input":const $=R.getAttribute("semantic"),st=o(R.getAttribute("source")),Tt=parseInt(R.getAttribute("offset"));v.inputs[$]={id:st,offset:Tt};break;case"vcount":v.vcount=a(R.textContent);break;case"v":v.v=a(R.textContent);break}}return v}function wt(x){const v={id:x.id},A=qt.geometries[v.id];return x.skin!==void 0&&(v.skin=X(x.skin),A.sources.skinIndices=v.skin.indices,A.sources.skinWeights=v.skin.weights),v}function X(x){const A={joints:[],indices:{array:[],stride:4},weights:{array:[],stride:4}},E=x.sources,R=x.vertexWeights,$=R.vcount,st=R.v,Tt=R.inputs.JOINT.offset,mt=R.inputs.WEIGHT.offset,bt=x.sources[x.joints.inputs.JOINT],Bt=x.sources[x.joints.inputs.INV_BIND_MATRIX],ht=E[R.inputs.WEIGHT.id].array;let kt=0,Nt,Gt,Vt;for(Nt=0,Vt=$.length;Nt<Vt;Nt++){const Se=$[Nt],_e=[];for(Gt=0;Gt<Se;Gt++){const ve=st[kt+Tt],$n=st[kt+mt],ln=ht[$n];_e.push({index:ve,weight:ln}),kt+=2}for(_e.sort(Ie),Gt=0;Gt<4;Gt++){const ve=_e[Gt];ve!==void 0?(A.indices.array.push(ve.index),A.weights.array.push(ve.weight)):(A.indices.array.push(0),A.weights.array.push(0))}}for(x.bindShapeMatrix?A.bindMatrix=new jt().fromArray(x.bindShapeMatrix).transpose():A.bindMatrix=new jt().identity(),Nt=0,Vt=bt.array.length;Nt<Vt;Nt++){const Se=bt.array[Nt],_e=new jt().fromArray(Bt.array,Nt*Bt.stride).transpose();A.joints.push({name:Se,boneInverse:_e})}return A;function Ie(Se,_e){return _e.weight-Se.weight}}function K(x){return _(qt.controllers[x],wt)}function nt(x){const v={init_from:n(x,"init_from")[0].textContent};qt.images[x.getAttribute("id")]=v}function it(x){return x.build!==void 0?x.build:x.init_from}function vt(x){const v=qt.images[x];return v!==void 0?_(v,it):(console.warn("THREE.ColladaLoader: Couldn't find image with ID:",x),null)}function zt(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"profile_COMMON":v.profile=Zt(R);break}}qt.effects[x.getAttribute("id")]=v}function Zt(x){const v={surfaces:{},samplers:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"newparam":Ce(R,v);break;case"technique":v.technique=G(R);break;case"extra":v.extra=Ht(R);break}}return v}function Ce(x,v){const A=x.getAttribute("sid");for(let E=0,R=x.childNodes.length;E<R;E++){const $=x.childNodes[E];if($.nodeType===1)switch($.nodeName){case"surface":v.surfaces[A]=ue($);break;case"sampler2D":v.samplers[A]=De($);break}}}function ue(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"init_from":v.init_from=R.textContent;break}}return v}function De(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"source":v.source=R.textContent;break}}return v}function G(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"constant":case"lambert":case"blinn":case"phong":v.type=R.nodeName,v.parameters=on(R);break;case"extra":v.extra=Ht(R);break}}return v}function on(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"emission":case"diffuse":case"specular":case"bump":case"ambient":case"shininess":case"transparency":v[R.nodeName]=ae(R);break;case"transparent":v[R.nodeName]={opaque:R.hasAttribute("opaque")?R.getAttribute("opaque"):"A_ONE",data:ae(R)};break}}return v}function ae(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"color":v[R.nodeName]=r(R.textContent);break;case"float":v[R.nodeName]=parseFloat(R.textContent);break;case"texture":v[R.nodeName]={id:R.getAttribute("texture"),extra:ce(R)};break}}return v}function ce(x){const v={technique:{}};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"extra":Wt(R,v);break}}return v}function Wt(x,v){for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"technique":Ae(R,v);break}}}function Ae(x,v){for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"repeatU":case"repeatV":case"offsetU":case"offsetV":v.technique[R.nodeName]=parseFloat(R.textContent);break;case"wrapU":case"wrapV":R.textContent.toUpperCase()==="TRUE"?v.technique[R.nodeName]=1:R.textContent.toUpperCase()==="FALSE"?v.technique[R.nodeName]=0:v.technique[R.nodeName]=parseInt(R.textContent);break;case"bump":v[R.nodeName]=b(R);break}}}function Ht(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"technique":v.technique=I(R);break}}return v}function I(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"double_sided":v[R.nodeName]=parseInt(R.textContent);break;case"bump":v[R.nodeName]=b(R);break}}return v}function b(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"texture":v[R.nodeName]={id:R.getAttribute("texture"),texcoord:R.getAttribute("texcoord"),extra:ce(R)};break}}return v}function q(x){return x}function ot(x){return _(qt.effects[x],q)}function lt(x){const v={name:x.getAttribute("name")};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"instance_effect":v.url=o(R.getAttribute("url"));break}}qt.materials[x.getAttribute("id")]=v}function rt(x){let v,A=x.slice((x.lastIndexOf(".")-1>>>0)+2);switch(A=A.toLowerCase(),A){case"tga":v=Sn;break;default:v=Nn}return v}function Ft(x){const v=ot(x.url),A=v.profile.technique;let E;switch(A.type){case"phong":case"blinn":E=new Ms;break;case"lambert":E=new ev;break;default:E=new je;break}E.name=x.name||"";function R(mt,bt=null){const Bt=v.profile.samplers[mt.id];let ht=null;if(Bt!==void 0){const kt=v.profile.surfaces[Bt.source];ht=vt(kt.init_from)}else console.warn("THREE.ColladaLoader: Undefined sampler. Access image directly (see #12530)."),ht=vt(mt.id);if(ht!==null){const kt=rt(ht);if(kt!==void 0){const Nt=kt.load(ht),Gt=mt.extra;if(Gt!==void 0&&Gt.technique!==void 0&&l(Gt.technique)===!1){const Vt=Gt.technique;Nt.wrapS=Vt.wrapU?Wi:On,Nt.wrapT=Vt.wrapV?Wi:On,Nt.offset.set(Vt.offsetU||0,Vt.offsetV||0),Nt.repeat.set(Vt.repeatU||1,Vt.repeatV||1)}else Nt.wrapS=Wi,Nt.wrapT=Wi;return bt!==null&&(Nt.colorSpace=bt),Nt}else return console.warn("THREE.ColladaLoader: Loader for texture %s not found.",ht),null}else return console.warn("THREE.ColladaLoader: Couldn't create texture with ID:",mt.id),null}const $=A.parameters;for(const mt in $){const bt=$[mt];switch(mt){case"diffuse":bt.color&&E.color.fromArray(bt.color),bt.texture&&(E.map=R(bt.texture,Le));break;case"specular":bt.color&&E.specular&&E.specular.fromArray(bt.color),bt.texture&&(E.specularMap=R(bt.texture));break;case"bump":bt.texture&&(E.normalMap=R(bt.texture));break;case"ambient":bt.texture&&(E.lightMap=R(bt.texture,Le));break;case"shininess":bt.float&&E.shininess&&(E.shininess=bt.float);break;case"emission":bt.color&&E.emissive&&E.emissive.fromArray(bt.color),bt.texture&&(E.emissiveMap=R(bt.texture,Le));break}}le.toWorkingColorSpace(E.color,Le),E.specular&&le.toWorkingColorSpace(E.specular,Le),E.emissive&&le.toWorkingColorSpace(E.emissive,Le);let st=$.transparent,Tt=$.transparency;if(Tt===void 0&&st&&(Tt={float:1}),st===void 0&&Tt&&(st={opaque:"A_ONE",data:{color:[1,1,1,1]}}),st&&Tt)if(st.data.texture)E.transparent=!0;else{const mt=st.data.color;switch(st.opaque){case"A_ONE":E.opacity=mt[3]*Tt.float;break;case"RGB_ZERO":E.opacity=1-mt[0]*Tt.float;break;case"A_ZERO":E.opacity=1-mt[3]*Tt.float;break;case"RGB_ONE":E.opacity=mt[0]*Tt.float;break;default:console.warn('THREE.ColladaLoader: Invalid opaque type "%s" of transparent tag.',st.opaque)}E.opacity<1&&(E.transparent=!0)}if(A.extra!==void 0&&A.extra.technique!==void 0){const mt=A.extra.technique;for(const bt in mt){const Bt=mt[bt];switch(bt){case"double_sided":E.side=Bt===1?un:ai;break;case"bump":E.normalMap=R(Bt.texture),E.normalScale=new At(1,1);break}}}return E}function Mt(x){return _(qt.materials[x],Ft)}function Ct(x){const v={name:x.getAttribute("name")};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"optics":v.optics=de(R);break}}qt.cameras[x.getAttribute("id")]=v}function de(x){for(let v=0;v<x.childNodes.length;v++){const A=x.childNodes[v];switch(A.nodeName){case"technique_common":return dt(A)}}return{}}function dt(x){const v={};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];switch(E.nodeName){case"perspective":case"orthographic":v.technique=E.nodeName,v.parameters=Pt(E);break}}return v}function Pt(x){const v={};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];switch(E.nodeName){case"xfov":case"yfov":case"xmag":case"ymag":case"znear":case"zfar":case"aspect_ratio":v[E.nodeName]=parseFloat(E.textContent);break}}return v}function Xt(x){let v;switch(x.optics.technique){case"perspective":v=new Je(x.optics.parameters.yfov,x.optics.parameters.aspect_ratio,x.optics.parameters.znear,x.optics.parameters.zfar);break;case"orthographic":let A=x.optics.parameters.ymag,E=x.optics.parameters.xmag;const R=x.optics.parameters.aspect_ratio;E=E===void 0?A*R:E,A=A===void 0?E/R:A,E*=.5,A*=.5,v=new Xc(-E,E,A,-A,x.optics.parameters.znear,x.optics.parameters.zfar);break;default:v=new Je;break}return v.name=x.name||"",v}function Yt(x){const v=qt.cameras[x];return v!==void 0?_(v,Xt):(console.warn("THREE.ColladaLoader: Couldn't find camera with ID:",x),null)}function Lt(x){let v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"technique_common":v=he(R);break}}qt.lights[x.getAttribute("id")]=v}function he(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"directional":case"point":case"spot":case"ambient":v.technique=R.nodeName,v.parameters=ee(R)}}return v}function ee(x){const v={};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"color":const $=r(R.textContent);v.color=new Kt().fromArray($),le.toWorkingColorSpace(v.color,Le);break;case"falloff_angle":v.falloffAngle=parseFloat(R.textContent);break;case"quadratic_attenuation":const st=parseFloat(R.textContent);v.distance=st?Math.sqrt(1/st):0;break}}return v}function ye(x){let v;switch(x.technique){case"directional":v=new Uu;break;case"point":v=new _v;break;case"spot":v=new mv;break;case"ambient":v=new xv;break}return x.parameters.color&&v.color.copy(x.parameters.color),x.parameters.distance&&(v.distance=x.parameters.distance),v}function z(x){const v=qt.lights[x];return v!==void 0?_(v,ye):(console.warn("THREE.ColladaLoader: Couldn't find light with ID:",x),null)}function xt(x){const v={name:x.getAttribute("name"),sources:{},vertices:{},primitives:[]},A=n(x,"mesh")[0];if(A!==void 0){for(let E=0;E<A.childNodes.length;E++){const R=A.childNodes[E];if(R.nodeType!==1)continue;const $=R.getAttribute("id");switch(R.nodeName){case"source":v.sources[$]=Z(R);break;case"vertices":v.vertices=at(R);break;case"polygons":console.warn("THREE.ColladaLoader: Unsupported primitive type: ",R.nodeName);break;case"lines":case"linestrips":case"polylist":case"triangles":v.primitives.push(Et(R));break;default:console.log(R)}}qt.geometries[x.getAttribute("id")]=v}}function Z(x){const v={array:[],stride:3};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"float_array":v.array=r(E.textContent);break;case"Name_array":v.array=s(E.textContent);break;case"technique_common":const R=n(E,"accessor")[0];R!==void 0&&(v.stride=parseInt(R.getAttribute("stride")));break}}return v}function at(x){const v={};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];E.nodeType===1&&(v[E.getAttribute("semantic")]=o(E.getAttribute("source")))}return v}function Et(x){const v={type:x.nodeName,material:x.getAttribute("material"),count:parseInt(x.getAttribute("count")),inputs:{},stride:0,hasUV:!1};for(let A=0,E=x.childNodes.length;A<E;A++){const R=x.childNodes[A];if(R.nodeType===1)switch(R.nodeName){case"input":const $=o(R.getAttribute("source")),st=R.getAttribute("semantic"),Tt=parseInt(R.getAttribute("offset")),mt=parseInt(R.getAttribute("set")),bt=mt>0?st+mt:st;v.inputs[bt]={id:$,offset:Tt},v.stride=Math.max(v.stride,Tt+1),st==="TEXCOORD"&&(v.hasUV=!0);break;case"vcount":v.vcount=a(R.textContent);break;case"p":v.p=a(R.textContent);break}}return v}function St(x){const v={};for(let A=0;A<x.length;A++){const E=x[A];v[E.type]===void 0&&(v[E.type]=[]),v[E.type].push(E)}return v}function Qt(x){let v=0;for(let A=0,E=x.length;A<E;A++)x[A].hasUV===!0&&v++;v>0&&v<x.length&&(x.uvsNeedsFix=!0)}function Re(x){const v={},A=x.sources,E=x.vertices,R=x.primitives;if(R.length===0)return{};const $=St(R);for(const st in $){const Tt=$[st];Qt(Tt),v[st]=We(Tt,A,E)}return v}function We(x,v,A){const E={},R={array:[],stride:0},$={array:[],stride:0},st={array:[],stride:0},Tt={array:[],stride:0},mt={array:[],stride:0},bt={array:[],stride:4},Bt={array:[],stride:4},ht=new Pe,kt=[];let Nt=0;for(let Gt=0;Gt<x.length;Gt++){const Vt=x[Gt],Ie=Vt.inputs;let Se=0;switch(Vt.type){case"lines":case"linestrips":Se=Vt.count*2;break;case"triangles":Se=Vt.count*3;break;case"polylist":for(let _e=0;_e<Vt.count;_e++){const ve=Vt.vcount[_e];switch(ve){case 3:Se+=3;break;case 4:Se+=6;break;default:Se+=(ve-2)*3;break}}break;default:console.warn("THREE.ColladaLoader: Unknow primitive type:",Vt.type)}ht.addGroup(Nt,Se,Gt),Nt+=Se,Vt.material&&kt.push(Vt.material);for(const _e in Ie){const ve=Ie[_e];switch(_e){case"VERTEX":for(const $n in A){const ln=A[$n];switch($n){case"POSITION":const Zi=R.array.length;if(ie(Vt,v[ln],ve.offset,R.array),R.stride=v[ln].stride,v.skinWeights&&v.skinIndices&&(ie(Vt,v.skinIndices,ve.offset,bt.array),ie(Vt,v.skinWeights,ve.offset,Bt.array)),Vt.hasUV===!1&&x.uvsNeedsFix===!0){const md=(R.array.length-Zi)/R.stride;for(let ol=0;ol<md;ol++)st.array.push(0,0)}break;case"NORMAL":ie(Vt,v[ln],ve.offset,$.array),$.stride=v[ln].stride;break;case"COLOR":ie(Vt,v[ln],ve.offset,mt.array),mt.stride=v[ln].stride;break;case"TEXCOORD":ie(Vt,v[ln],ve.offset,st.array),st.stride=v[ln].stride;break;case"TEXCOORD1":ie(Vt,v[ln],ve.offset,Tt.array),st.stride=v[ln].stride;break;default:console.warn('THREE.ColladaLoader: Semantic "%s" not handled in geometry build process.',$n)}}break;case"NORMAL":ie(Vt,v[ve.id],ve.offset,$.array),$.stride=v[ve.id].stride;break;case"COLOR":ie(Vt,v[ve.id],ve.offset,mt.array,!0),mt.stride=v[ve.id].stride;break;case"TEXCOORD":ie(Vt,v[ve.id],ve.offset,st.array),st.stride=v[ve.id].stride;break;case"TEXCOORD1":ie(Vt,v[ve.id],ve.offset,Tt.array),Tt.stride=v[ve.id].stride;break}}}return R.array.length>0&&ht.setAttribute("position",new ne(R.array,R.stride)),$.array.length>0&&ht.setAttribute("normal",new ne($.array,$.stride)),mt.array.length>0&&ht.setAttribute("color",new ne(mt.array,mt.stride)),st.array.length>0&&ht.setAttribute("uv",new ne(st.array,st.stride)),Tt.array.length>0&&ht.setAttribute("uv1",new ne(Tt.array,Tt.stride)),bt.array.length>0&&ht.setAttribute("skinIndex",new ne(bt.array,bt.stride)),Bt.array.length>0&&ht.setAttribute("skinWeight",new ne(Bt.array,Bt.stride)),E.data=ht,E.type=x[0].type,E.materialKeys=kt,E}function ie(x,v,A,E,R=!1){const $=x.p,st=x.stride,Tt=x.vcount;function mt(ht){let kt=$[ht+A]*Bt;const Nt=kt+Bt;for(;kt<Nt;kt++)E.push(bt[kt]);if(R){const Gt=E.length-Bt-1;Di.setRGB(E[Gt+0],E[Gt+1],E[Gt+2],Le),E[Gt+0]=Di.r,E[Gt+1]=Di.g,E[Gt+2]=Di.b}}const bt=v.array,Bt=v.stride;if(x.vcount!==void 0){let ht=0;for(let kt=0,Nt=Tt.length;kt<Nt;kt++){const Gt=Tt[kt];if(Gt===4){const Vt=ht+st*0,Ie=ht+st*1,Se=ht+st*2,_e=ht+st*3;mt(Vt),mt(Ie),mt(_e),mt(Ie),mt(Se),mt(_e)}else if(Gt===3){const Vt=ht+st*0,Ie=ht+st*1,Se=ht+st*2;mt(Vt),mt(Ie),mt(Se)}else if(Gt>4)for(let Vt=1,Ie=Gt-2;Vt<=Ie;Vt++){const Se=ht+st*0,_e=ht+st*Vt,ve=ht+st*(Vt+1);mt(Se),mt(_e),mt(ve)}ht+=st*Gt}}else for(let ht=0,kt=$.length;ht<kt;ht+=st)mt(ht)}function an(x){return _(qt.geometries[x],Re)}function Pn(x){const v={name:x.getAttribute("name")||"",joints:{},links:[]};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"technique_common":Yn(E,v);break}}qt.kinematicsModels[x.getAttribute("id")]=v}function Sr(x){return x.build!==void 0?x.build:x}function br(x){return _(qt.kinematicsModels[x],Sr)}function Yn(x,v){for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"joint":v.joints[E.getAttribute("sid")]=Gs(E);break;case"link":v.links.push(Ws(E));break}}}function Gs(x){let v;for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"prismatic":case"revolute":v=Er(E);break}}return v}function Er(x){const v={sid:x.getAttribute("sid"),name:x.getAttribute("name")||"",axis:new L,limits:{min:0,max:0},type:x.nodeName,static:!1,zeroPosition:0,middlePosition:0};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"axis":const R=r(E.textContent);v.axis.fromArray(R);break;case"limits":const $=E.getElementsByTagName("max")[0],st=E.getElementsByTagName("min")[0];v.limits.max=parseFloat($.textContent),v.limits.min=parseFloat(st.textContent);break}}return v.limits.min>=v.limits.max&&(v.static=!0),v.middlePosition=(v.limits.min+v.limits.max)/2,v}function Ws(x){const v={sid:x.getAttribute("sid"),name:x.getAttribute("name")||"",attachments:[],transforms:[]};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"attachment_full":v.attachments.push(Ki(E));break;case"matrix":case"translate":case"rotate":v.transforms.push(Xs(E));break}}return v}function Ki(x){const v={joint:x.getAttribute("joint").split("/").pop(),transforms:[],links:[]};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"link":v.links.push(Ws(E));break;case"matrix":case"translate":case"rotate":v.transforms.push(Xs(E));break}}return v}function Xs(x){const v={type:x.nodeName},A=r(x.textContent);switch(v.type){case"matrix":v.obj=new jt,v.obj.fromArray(A).transpose();break;case"translate":v.obj=new L,v.obj.fromArray(A);break;case"rotate":v.obj=new L,v.obj.fromArray(A),v.angle=ps.degToRad(A[3]);break}return v}function Ji(x){const v={name:x.getAttribute("name")||"",rigidBodies:{}};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"rigid_body":v.rigidBodies[E.getAttribute("name")]={},wr(E,v.rigidBodies[E.getAttribute("name")]);break}}qt.physicsModels[x.getAttribute("id")]=v}function wr(x,v){for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"technique_common":Tr(E,v);break}}}function Tr(x,v){for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"inertia":v.inertia=r(E.textContent);break;case"mass":v.mass=r(E.textContent)[0];break}}}function Yo(x){const v={bindJointAxis:[]};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"bind_joint_axis":v.bindJointAxis.push($o(E));break}}qt.kinematicsScenes[o(x.getAttribute("url"))]=v}function $o(x){const v={target:x.getAttribute("target").split("/").pop()};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType===1)switch(E.nodeName){case"axis":const R=E.getElementsByTagName("param")[0];v.axis=R.textContent;const $=v.axis.split("inst_").pop().split("axis")[0];v.jointIndex=$.substring(0,$.length-1);break}}return v}function Ko(x){return x.build!==void 0?x.build:x}function C(x){return _(qt.kinematicsScenes[x],Ko)}function V(){const x=Object.keys(qt.kinematicsModels)[0],v=Object.keys(qt.kinematicsScenes)[0],A=Object.keys(qt.visualScenes)[0];if(x===void 0||v===void 0)return;const E=br(x),R=C(v),$=pe(A),st=R.bindJointAxis,Tt={};for(let Bt=0,ht=st.length;Bt<ht;Bt++){const kt=st[Bt],Nt=Jt.querySelector('[sid="'+kt.target+'"]');if(Nt){const Gt=Nt.parentElement;mt(kt.jointIndex,Gt)}}function mt(Bt,ht){const kt=ht.getAttribute("name"),Nt=E.joints[Bt];$.traverse(function(Gt){Gt.name===kt&&(Tt[Bt]={object:Gt,transforms:j(ht),joint:Nt,position:Nt.zeroPosition})})}const bt=new jt;rl={joints:E&&E.joints,getJointValue:function(Bt){const ht=Tt[Bt];if(ht)return ht.position;console.warn("THREE.ColladaLoader: Joint "+Bt+" doesn't exist.")},setJointValue:function(Bt,ht){const kt=Tt[Bt];if(kt){const Nt=kt.joint;if(ht>Nt.limits.max||ht<Nt.limits.min)console.warn("THREE.ColladaLoader: Joint "+Bt+" value "+ht+" outside of limits (min: "+Nt.limits.min+", max: "+Nt.limits.max+").");else if(Nt.static)console.warn("THREE.ColladaLoader: Joint "+Bt+" is static.");else{const Gt=kt.object,Vt=Nt.axis,Ie=kt.transforms;B.identity();for(let Se=0;Se<Ie.length;Se++){const _e=Ie[Se];if(_e.sid&&_e.sid.indexOf(Bt)!==-1)switch(Nt.type){case"revolute":B.multiply(bt.makeRotationAxis(Vt,ps.degToRad(ht)));break;case"prismatic":B.multiply(bt.makeTranslation(Vt.x*ht,Vt.y*ht,Vt.z*ht));break;default:console.warn("THREE.ColladaLoader: Unknown joint type: "+Nt.type);break}else switch(_e.type){case"matrix":B.multiply(_e.obj);break;case"translate":B.multiply(bt.makeTranslation(_e.obj.x,_e.obj.y,_e.obj.z));break;case"scale":B.scale(_e.obj);break;case"rotate":B.multiply(bt.makeRotationAxis(_e.obj,_e.angle));break}}Gt.matrix.copy(B),Gt.matrix.decompose(Gt.position,Gt.quaternion,Gt.scale),Tt[Bt].position=ht}}else console.log("THREE.ColladaLoader: "+Bt+" does not exist.")}}}function j(x){const v=[],A=Jt.querySelector('[id="'+x.id+'"]');for(let E=0;E<A.childNodes.length;E++){const R=A.childNodes[E];if(R.nodeType!==1)continue;let $,st;switch(R.nodeName){case"matrix":$=r(R.textContent);const Tt=new jt().fromArray($).transpose();v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:Tt});break;case"translate":case"scale":$=r(R.textContent),st=new L().fromArray($),v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:st});break;case"rotate":$=r(R.textContent),st=new L().fromArray($);const mt=ps.degToRad($[3]);v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:st,angle:mt});break}}return v}function Y(x){const v=x.getElementsByTagName("node");for(let A=0;A<v.length;A++){const E=v[A];E.hasAttribute("id")===!1&&E.setAttribute("id",c())}}const B=new jt,ut=new L;function yt(x){const v={name:x.getAttribute("name")||"",type:x.getAttribute("type"),id:x.getAttribute("id"),sid:x.getAttribute("sid"),matrix:new jt,nodes:[],instanceCameras:[],instanceControllers:[],instanceLights:[],instanceGeometries:[],instanceNodes:[],transforms:{}};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];if(E.nodeType!==1)continue;let R;switch(E.nodeName){case"node":v.nodes.push(E.getAttribute("id")),yt(E);break;case"instance_camera":v.instanceCameras.push(o(E.getAttribute("url")));break;case"instance_controller":v.instanceControllers.push(Dt(E));break;case"instance_light":v.instanceLights.push(o(E.getAttribute("url")));break;case"instance_geometry":v.instanceGeometries.push(Dt(E));break;case"instance_node":v.instanceNodes.push(o(E.getAttribute("url")));break;case"matrix":R=r(E.textContent),v.matrix.multiply(B.fromArray(R).transpose()),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"translate":R=r(E.textContent),ut.fromArray(R),v.matrix.multiply(B.makeTranslation(ut.x,ut.y,ut.z)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"rotate":R=r(E.textContent);const $=ps.degToRad(R[3]);v.matrix.multiply(B.makeRotationAxis(ut.fromArray(R),$)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"scale":R=r(E.textContent),v.matrix.scale(ut.fromArray(R)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"extra":break;default:console.log(E)}}return be(v.id)?console.warn("THREE.ColladaLoader: There is already a node with ID %s. Exclude current node from further processing.",v.id):qt.nodes[v.id]=v,v}function Dt(x){const v={id:o(x.getAttribute("url")),materials:{},skeletons:[]};for(let A=0;A<x.childNodes.length;A++){const E=x.childNodes[A];switch(E.nodeName){case"bind_material":const R=E.getElementsByTagName("instance_material");for(let $=0;$<R.length;$++){const st=R[$],Tt=st.getAttribute("symbol"),mt=st.getAttribute("target");v.materials[Tt]=o(mt)}break;case"skeleton":v.skeletons.push(o(E.textContent));break}}return v}function It(x,v){const A=[],E=[];let R,$,st;for(R=0;R<x.length;R++){const bt=x[R];let Bt;if(be(bt))Bt=Oe(bt),$t(Bt,v,A);else if(Ln(bt)){const kt=qt.visualScenes[bt].children;for(let Nt=0;Nt<kt.length;Nt++){const Gt=kt[Nt];if(Gt.type==="JOINT"){const Vt=Oe(Gt.id);$t(Vt,v,A)}}}else console.error("THREE.ColladaLoader: Unable to find root bone of skeleton with ID:",bt)}for(R=0;R<v.length;R++)for($=0;$<A.length;$++)if(st=A[$],st.bone.name===v[R].name){E[R]=st,st.processed=!0;break}for(R=0;R<A.length;R++)st=A[R],st.processed===!1&&(E.push(st),st.processed=!0);const Tt=[],mt=[];for(R=0;R<E.length;R++)st=E[R],Tt.push(st.bone),mt.push(st.boneInverse);return new Yc(Tt,mt)}function $t(x,v,A){x.traverse(function(E){if(E.isBone===!0){let R;for(let $=0;$<v.length;$++){const st=v[$];if(st.name===E.name){R=st.boneInverse;break}}R===void 0&&(R=new jt),A.push({bone:E,boneInverse:R,processed:!1})}})}function te(x){const v=[],A=x.matrix,E=x.nodes,R=x.type,$=x.instanceCameras,st=x.instanceControllers,Tt=x.instanceLights,mt=x.instanceGeometries,bt=x.instanceNodes;for(let ht=0,kt=E.length;ht<kt;ht++)v.push(Oe(E[ht]));for(let ht=0,kt=$.length;ht<kt;ht++){const Nt=Yt($[ht]);Nt!==null&&v.push(Nt.clone())}for(let ht=0,kt=st.length;ht<kt;ht++){const Nt=st[ht],Gt=K(Nt.id),Vt=an(Gt.id),Ie=Me(Vt,Nt.materials),Se=Nt.skeletons,_e=Gt.skin.joints,ve=It(Se,_e);for(let $n=0,ln=Ie.length;$n<ln;$n++){const Zi=Ie[$n];Zi.isSkinnedMesh&&(Zi.bind(ve,Gt.skin.bindMatrix),Zi.normalizeSkinWeights()),v.push(Zi)}}for(let ht=0,kt=Tt.length;ht<kt;ht++){const Nt=z(Tt[ht]);Nt!==null&&v.push(Nt.clone())}for(let ht=0,kt=mt.length;ht<kt;ht++){const Nt=mt[ht],Gt=an(Nt.id),Vt=Me(Gt,Nt.materials);for(let Ie=0,Se=Vt.length;Ie<Se;Ie++)v.push(Vt[Ie])}for(let ht=0,kt=bt.length;ht<kt;ht++)v.push(Oe(bt[ht]).clone());let Bt;if(E.length===0&&v.length===1)Bt=v[0];else{Bt=R==="JOINT"?new wu:new Fe;for(let ht=0;ht<v.length;ht++)Bt.add(v[ht])}return Bt.name=R==="JOINT"?x.sid:x.name,Bt.matrix.copy(A),Bt.matrix.decompose(Bt.position,Bt.quaternion,Bt.scale),Bt}const Ut=new je({name:hi.DEFAULT_MATERIAL_NAME,color:16711935});function fe(x,v){const A=[];for(let E=0,R=x.length;E<R;E++){const $=v[x[E]];$===void 0?(console.warn("THREE.ColladaLoader: Material with key %s not found. Apply fallback material.",x[E]),A.push(Ut)):A.push(Mt($))}return A}function Me(x,v){const A=[];for(const E in x){const R=x[E],$=fe(R.materialKeys,v);if($.length===0&&(E==="lines"||E==="linestrips"?$.push(new Bn):$.push(new Ms)),E==="lines"||E==="linestrips")for(let bt=0,Bt=$.length;bt<Bt;bt++){const ht=$[bt];if(ht.isMeshPhongMaterial===!0||ht.isMeshLambertMaterial===!0){const kt=new Bn;kt.color.copy(ht.color),kt.opacity=ht.opacity,kt.transparent=ht.transparent,$[bt]=kt}}const st=R.data.attributes.skinIndex!==void 0,Tt=$.length===1?$[0]:$;let mt;switch(E){case"lines":mt=new bo(R.data,Tt);break;case"linestrips":mt=new Bs(R.data,Tt);break;case"triangles":case"polylist":st?mt=new O0(R.data,Tt):mt=new me(R.data,Tt);break}A.push(mt)}return A}function be(x){return qt.nodes[x]!==void 0}function Oe(x){return _(qt.nodes[x],te)}function ge(x){const v={name:x.getAttribute("name"),children:[]};Y(x);const A=n(x,"node");for(let E=0;E<A.length;E++)v.children.push(yt(A[E]));qt.visualScenes[x.getAttribute("id")]=v}function Ot(x){const v=new Fe;v.name=x.name;const A=x.children;for(let E=0;E<A.length;E++){const R=A[E];v.add(Oe(R.id))}return v}function Ln(x){return qt.visualScenes[x]!==void 0}function pe(x){return _(qt.visualScenes[x],Ot)}function pn(x){const v=n(x,"instance_visual_scene")[0];return pe(o(v.getAttribute("url")))}function pi(){const x=qt.clips;if(l(x)===!0){if(l(qt.animations)===!1){const v=[];for(const A in qt.animations){const E=M(A);for(let R=0,$=E.length;R<$;R++)v.push(E[R])}Ar.push(new Eh("default",-1,v))}}else for(const v in x)Ar.push(W(v))}function Ze(x){let v="";const A=[x];for(;A.length;){const E=A.shift();E.nodeType===Node.TEXT_NODE?v+=E.textContent:(v+=`
`,A.push.apply(A,E.childNodes))}return v.trim()}if(t.length===0)return{scene:new Eu};const mi=new DOMParser().parseFromString(t,"application/xml"),Jt=n(mi,"COLLADA")[0],cn=mi.getElementsByTagName("parsererror")[0];if(cn!==void 0){const x=n(cn,"div")[0];let v;return x?v=x.textContent:v=Ze(cn),console.error(`THREE.ColladaLoader: Failed to parse collada file.
`,v),null}const Ni=Jt.getAttribute("version");console.debug("THREE.ColladaLoader: File version",Ni);const Qe=h(n(Jt,"asset")[0]),Nn=new Iu(this.manager);Nn.setPath(this.resourcePath||e).setCrossOrigin(this.crossOrigin);let Sn;Bh&&(Sn=new Bh(this.manager),Sn.setPath(this.resourcePath||e));const Di=new Kt,Ar=[];let rl={},pd=0;const qt={animations:{},clips:{},controllers:{},images:{},effects:{},materials:{},cameras:{},lights:{},geometries:{},nodes:{},visualScenes:{},kinematicsModels:{},physicsModels:{},kinematicsScenes:{}};p(Jt,"library_animations","animation",m),p(Jt,"library_animation_clips","animation_clip",O),p(Jt,"library_controllers","controller",ct),p(Jt,"library_images","image",nt),p(Jt,"library_effects","effect",zt),p(Jt,"library_materials","material",lt),p(Jt,"library_cameras","camera",Ct),p(Jt,"library_lights","light",Lt),p(Jt,"library_geometries","geometry",xt),p(Jt,"library_nodes","node",yt),p(Jt,"library_visual_scenes","visual_scene",ge),p(Jt,"library_kinematics_models","kinematics_model",Pn),p(Jt,"library_physics_models","physics_model",Ji),p(Jt,"scene","instance_kinematics_scene",Yo),g(qt.animations,T),g(qt.clips,tt),g(qt.controllers,wt),g(qt.images,it),g(qt.effects,q),g(qt.materials,Ft),g(qt.cameras,Xt),g(qt.lights,ye),g(qt.geometries,Re),g(qt.visualScenes,Ot),pi(),V();const Cr=pn(n(Jt,"scene")[0]);return Cr.animations=Ar,Qe.upAxis==="Z_UP"&&(console.warn("THREE.ColladaLoader: You are loading an asset with a Z-UP coordinate system. The loader just rotates the asset to transform it into Y-UP. The vertex data are not converted, see #24289."),Cr.rotation.set(-Math.PI/2,0,0)),Cr.scale.multiplyScalar(Qe.unit),{get animations(){return console.warn("THREE.ColladaLoader: Please access animations over scene.animations now."),Ar},kinematics:rl,library:qt,scene:Cr}}}const zh=new L,Wv=new fn,oo=new jt,Si=new jt,ao=new Vn,co=new L(1,1,1),lo=new L;class Go extends Ne{constructor(...t){super(...t),this.urdfNode=null,this.urdfName=""}copy(t,e){return super.copy(t,e),this.urdfNode=t.urdfNode,this.urdfName=t.urdfName,this}}class Xv extends Go{constructor(...t){super(...t),this.isURDFCollider=!0,this.type="URDFCollider"}}class qv extends Go{constructor(...t){super(...t),this.isURDFVisual=!0,this.type="URDFVisual"}}class ku extends Go{constructor(...t){super(...t),this.isURDFLink=!0,this.type="URDFLink",this.inertial={mass:0,origin:{xyz:[0,0,0],rpy:[0,0,0]},inertia:{ixx:0,ixy:0,ixz:0,iyy:0,iyz:0,izz:0}}}copy(t,e){return super.copy(t,e),this.inertial={mass:t.inertial.mass,origin:{xyz:[...t.inertial.origin.xyz],rpy:[...t.inertial.origin.rpy]},inertia:{...t.inertial.inertia}},this}}class Bu extends Go{get jointType(){return this._jointType}set jointType(t){if(this.jointType!==t)switch(this._jointType=t,this.matrixWorldNeedsUpdate=!0,t){case"fixed":this.jointValue=[];break;case"continuous":case"revolute":case"prismatic":this.jointValue=new Array(1).fill(0);break;case"planar":this.jointValue=new Array(3).fill(0),this.axis=new L(0,0,1);break;case"floating":this.jointValue=new Array(6).fill(0);break}}get angle(){return this.jointValue[0]}constructor(...t){super(...t),this.isURDFJoint=!0,this.type="URDFJoint",this.jointValue=null,this.jointType="fixed",this.axis=new L(1,0,0),this.limit={lower:0,upper:0,effort:0,velocity:0},this.ignoreLimits=!1,this.origPosition=null,this.origQuaternion=null,this.mimicJoints=[]}copy(t,e){return super.copy(t,e),this.jointType=t.jointType,this.axis=t.axis.clone(),this.limit.lower=t.limit.lower,this.limit.upper=t.limit.upper,this.limit.effort=t.limit.effort,this.limit.velocity=t.limit.velocity,this.ignoreLimits=!1,this.jointValue=[...t.jointValue],this.origPosition=t.origPosition?t.origPosition.clone():null,this.origQuaternion=t.origQuaternion?t.origQuaternion.clone():null,this.mimicJoints=[...t.mimicJoints],this}setJointValue(...t){t=t.map(n=>n===null?null:parseFloat(n)),(!this.origPosition||!this.origQuaternion)&&(this.origPosition=this.position.clone(),this.origQuaternion=this.quaternion.clone());let e=!1;switch(this.mimicJoints.forEach(n=>{e=n.updateFromMimickedJoint(...t)||e}),this.jointType){case"fixed":return e;case"continuous":case"revolute":{let n=t[0];return n==null||n===this.jointValue[0]?e:(!this.ignoreLimits&&this.jointType==="revolute"&&(n=Math.min(this.limit.upper,n),n=Math.max(this.limit.lower,n)),this.quaternion.setFromAxisAngle(this.axis,n).premultiply(this.origQuaternion),this.jointValue[0]!==n?(this.jointValue[0]=n,this.matrixWorldNeedsUpdate=!0,!0):e)}case"prismatic":{let n=t[0];return n==null||n===this.jointValue[0]?e:(this.ignoreLimits||(n=Math.min(this.limit.upper,n),n=Math.max(this.limit.lower,n)),this.position.copy(this.origPosition),zh.copy(this.axis).applyEuler(this.rotation),this.position.addScaledVector(zh,n),this.jointValue[0]!==n?(this.jointValue[0]=n,this.matrixWorldNeedsUpdate=!0,!0):e)}case"floating":return this.jointValue.every((n,s)=>t[s]===n||t[s]===null)?e:(this.jointValue[0]=t[0]!==null?t[0]:this.jointValue[0],this.jointValue[1]=t[1]!==null?t[1]:this.jointValue[1],this.jointValue[2]=t[2]!==null?t[2]:this.jointValue[2],this.jointValue[3]=t[3]!==null?t[3]:this.jointValue[3],this.jointValue[4]=t[4]!==null?t[4]:this.jointValue[4],this.jointValue[5]=t[5]!==null?t[5]:this.jointValue[5],Si.compose(this.origPosition,this.origQuaternion,co),ao.setFromEuler(Wv.set(this.jointValue[3],this.jointValue[4],this.jointValue[5],"XYZ")),lo.set(this.jointValue[0],this.jointValue[1],this.jointValue[2]),oo.compose(lo,ao,co),Si.premultiply(oo),this.position.setFromMatrixPosition(Si),this.rotation.setFromRotationMatrix(Si),this.matrixWorldNeedsUpdate=!0,!0);case"planar":return this.jointValue.every((n,s)=>t[s]===n||t[s]===null)?e:(this.jointValue[0]=t[0]!==null?t[0]:this.jointValue[0],this.jointValue[1]=t[1]!==null?t[1]:this.jointValue[1],this.jointValue[2]=t[2]!==null?t[2]:this.jointValue[2],Si.compose(this.origPosition,this.origQuaternion,co),ao.setFromAxisAngle(this.axis,this.jointValue[2]),lo.set(this.jointValue[0],this.jointValue[1],0),oo.compose(lo,ao,co),Si.premultiply(oo),this.position.setFromMatrixPosition(Si),this.rotation.setFromRotationMatrix(Si),this.matrixWorldNeedsUpdate=!0,!0)}return e}}class Vh extends Bu{constructor(...t){super(...t),this.type="URDFMimicJoint",this.mimicJoint=null,this.offset=0,this.multiplier=1}updateFromMimickedJoint(...t){const e=t.map(n=>n===null?null:n*this.multiplier+this.offset);return super.setJointValue(...e)}copy(t,e){return super.copy(t,e),this.mimicJoint=t.mimicJoint,this.offset=t.offset,this.multiplier=t.multiplier,this}}class jv extends ku{constructor(...t){super(...t),this.isURDFRobot=!0,this.urdfNode=null,this.urdfRobotNode=null,this.robotName=null,this.links=null,this.joints=null,this.colliders=null,this.visual=null,this.frames=null}copy(t,e){super.copy(t,e),this.urdfRobotNode=t.urdfRobotNode,this.robotName=t.robotName,this.links={},this.joints={},this.colliders={},this.visual={},this.traverse(n=>{n.isURDFJoint&&n.urdfName in t.joints&&(this.joints[n.urdfName]=n),n.isURDFLink&&n.urdfName in t.links&&(this.links[n.urdfName]=n),n.isURDFCollider&&n.urdfName in t.colliders&&(this.colliders[n.urdfName]=n),n.isURDFVisual&&n.urdfName in t.visual&&(this.visual[n.urdfName]=n)});for(const n in this.joints)this.joints[n].mimicJoints=this.joints[n].mimicJoints.map(s=>this.joints[s.name]);return this.frames={...this.colliders,...this.visual,...this.links,...this.joints},this}getFrame(t){return this.frames[t]}setJointValue(t,...e){const n=this.joints[t];return n?n.setJointValue(...e):!1}setJointValues(t){let e=!1;for(const n in t){const s=t[n];Array.isArray(s)?e=this.setJointValue(n,...s)||e:e=this.setJointValue(n,s)||e}return e}}const ka=new Vn,Hh=new fn;function bi(i){return i?i.trim().split(/\s+/g).map(t=>parseFloat(t)):[0,0,0]}function Gh(i,t,e=!1){e||i.rotation.set(0,0,0),Hh.set(t[0],t[1],t[2],"ZYX"),ka.setFromEuler(Hh),ka.multiply(i.quaternion),i.quaternion.copy(ka)}class Yv{constructor(t){this.manager=t||Du,this.loadMeshCb=this.defaultMeshLoader.bind(this),this.parseVisual=!0,this.parseCollision=!1,this.packages="",this.workingPath="",this.fetchOptions={}}loadAsync(t){return new Promise((e,n)=>{this.load(t,e,null,n)})}load(t,e,n,s){const r=this.manager,a=Fu.extractUrlBase(t),o=this.manager.resolveURL(t);r.itemStart(o),fetch(o,this.fetchOptions).then(c=>{if(c.ok)return n&&n(null),c.text();throw new Error(`URDFLoader: Failed to load url '${o}' with error code ${c.status} : ${c.statusText}.`)}).then(c=>{const l=this.parse(c,this.workingPath||a);e(l),r.itemEnd(o)}).catch(c=>{s?s(c):console.error("URDFLoader: Error loading file.",c),r.itemError(o),r.itemEnd(o)})}parse(t,e=this.workingPath){const n=this.packages,s=this.loadMeshCb,r=this.parseVisual,a=this.parseCollision,o=this.manager,c={},l={},h={};function u(w){if(!/^package:\/\//.test(w))return e?e+w:w;const[T,M]=w.replace(/^package:\/\//,"").split(/\/(.+)/);if(typeof n=="string")return n.endsWith(T)?n+"/"+M:n+"/"+T+"/"+M;if(typeof n=="function")return n(T)+"/"+M;if(typeof n=="object")return T in n?n[T]+"/"+M:(console.error(`URDFLoader : ${T} not found in provided package list.`),null)}function f(w){let T;w instanceof Document?T=[...w.children]:w instanceof Element?T=[w]:T=[...new DOMParser().parseFromString(w,"text/xml").children];const M=T.filter(F=>F.nodeName==="robot").pop();return p(M)}function p(w){const T=[...w.children],M=T.filter(U=>U.nodeName.toLowerCase()==="link"),F=T.filter(U=>U.nodeName.toLowerCase()==="joint"),P=T.filter(U=>U.nodeName.toLowerCase()==="material"),N=new jv;N.robotName=w.getAttribute("name"),N.urdfRobotNode=w,P.forEach(U=>{const k=U.getAttribute("name");h[k]=m(U)});const D={},y={};M.forEach(U=>{const k=U.getAttribute("name"),H=w.querySelector(`child[link="${k}"]`)===null;c[k]=_(U,D,y,H?N:null)}),F.forEach(U=>{const k=U.getAttribute("name");l[k]=g(U)}),N.joints=l,N.links=c,N.colliders=y,N.visual=D;const S=Object.values(l);return S.forEach(U=>{U instanceof Vh&&l[U.mimicJoint].mimicJoints.push(U)}),S.forEach(U=>{const k=new Set,H=J=>{if(k.has(J))throw new Error("URDFLoader: Detected an infinite loop of mimic joints.");k.add(J),J.mimicJoints.forEach(Q=>{H(Q)})};H(U)}),N.frames={...y,...D,...c,...l},N}function g(w){const T=[...w.children],M=w.getAttribute("type");let F;const P=T.find(k=>k.nodeName.toLowerCase()==="mimic");P?(F=new Vh,F.mimicJoint=P.getAttribute("joint"),F.multiplier=parseFloat(P.getAttribute("multiplier")||1),F.offset=parseFloat(P.getAttribute("offset")||0)):F=new Bu,F.urdfNode=w,F.name=w.getAttribute("name"),F.urdfName=F.name,F.jointType=M;let N=null,D=null,y=[0,0,0],S=[0,0,0];T.forEach(k=>{const H=k.nodeName.toLowerCase();H==="origin"?(y=bi(k.getAttribute("xyz")),S=bi(k.getAttribute("rpy"))):H==="child"?D=c[k.getAttribute("link")]:H==="parent"?N=c[k.getAttribute("link")]:H==="limit"&&(F.limit.lower=parseFloat(k.getAttribute("lower")||F.limit.lower),F.limit.upper=parseFloat(k.getAttribute("upper")||F.limit.upper),F.limit.effort=parseFloat(k.getAttribute("effort")||F.limit.effort),F.limit.velocity=parseFloat(k.getAttribute("velocity")||F.limit.velocity))}),N.add(F),F.add(D),Gh(F,S),F.position.set(y[0],y[1],y[2]);const U=T.filter(k=>k.nodeName.toLowerCase()==="axis")[0];if(U){const k=U.getAttribute("xyz").split(/\s+/g).map(H=>parseFloat(H));F.axis=new L(k[0],k[1],k[2]),F.axis.normalize()}return F}function _(w,T,M,F=null){F===null&&(F=new ku);const P=[...w.children];F.name=w.getAttribute("name"),F.urdfName=F.name,F.urdfNode=w;const N=P.find(D=>D.nodeName.toLowerCase()==="inertial");return N&&[...N.children].forEach(D=>{const y=D.nodeName.toLowerCase();y==="origin"?(F.inertial.origin.xyz=bi(D.getAttribute("xyz")),F.inertial.origin.rpy=bi(D.getAttribute("rpy"))):y==="mass"?F.inertial.mass=parseFloat(D.getAttribute("value"))||0:y==="inertia"&&(F.inertial.inertia.ixx=parseFloat(D.getAttribute("ixx"))||0,F.inertial.inertia.ixy=parseFloat(D.getAttribute("ixy"))||0,F.inertial.inertia.ixz=parseFloat(D.getAttribute("ixz"))||0,F.inertial.inertia.iyy=parseFloat(D.getAttribute("iyy"))||0,F.inertial.inertia.iyz=parseFloat(D.getAttribute("iyz"))||0,F.inertial.inertia.izz=parseFloat(D.getAttribute("izz"))||0)}),r&&P.filter(y=>y.nodeName.toLowerCase()==="visual").forEach(y=>{const S=d(y,h);if(F.add(S),y.hasAttribute("name")){const U=y.getAttribute("name");S.name=U,S.urdfName=U,T[U]=S}}),a&&P.filter(y=>y.nodeName.toLowerCase()==="collision").forEach(y=>{const S=d(y);if(F.add(S),y.hasAttribute("name")){const U=y.getAttribute("name");S.name=U,S.urdfName=U,M[U]=S}}),F}function m(w){const T=[...w.children],M=new Ms;return M.name=w.getAttribute("name")||"",T.forEach(F=>{const P=F.nodeName.toLowerCase();if(P==="color"){const N=F.getAttribute("rgba").split(/\s/g).map(D=>parseFloat(D));M.color.setRGB(N[0],N[1],N[2]),M.opacity=N[3],M.transparent=N[3]<1,M.depthWrite=!M.transparent}else if(P==="texture"){const N=F.getAttribute("filename");if(N){const D=new Iu(o),y=u(N);M.map=D.load(y),M.map.colorSpace=Le}}}),M}function d(w,T={}){const M=w.nodeName.toLowerCase()==="collision",F=[...w.children];let P=null;const N=F.filter(y=>y.nodeName.toLowerCase()==="material")[0];if(N){const y=N.getAttribute("name");y&&y in T?P=T[y]:P=m(N)}else P=new Ms;const D=M?new Xv:new qv;return D.urdfNode=w,F.forEach(y=>{const S=y.nodeName.toLowerCase();if(S==="geometry"){const U=y.children[0].nodeName.toLowerCase();if(U==="mesh"){const k=y.children[0].getAttribute("filename"),H=u(k);if(H!==null){const J=y.children[0].getAttribute("scale");if(J){const Q=bi(J);D.scale.set(Q[0],Q[1],Q[2])}s(H,o,(Q,O)=>{O?console.error("URDFLoader: Error loading mesh.",O):Q&&(Q instanceof me&&(Q.material=P),Q.position.set(0,0,0),Q.quaternion.identity(),D.add(Q))})}}else if(U==="box"){const k=new me;k.geometry=new Os(1,1,1),k.material=P;const H=bi(y.children[0].getAttribute("size"));k.scale.set(H[0],H[1],H[2]),D.add(k)}else if(U==="sphere"){const k=new me;k.geometry=new li(1,30,30),k.material=P;const H=parseFloat(y.children[0].getAttribute("radius"))||0;k.scale.set(H,H,H),D.add(k)}else if(U==="cylinder"){const k=new me;k.geometry=new zs(1,1,1,30),k.material=P;const H=parseFloat(y.children[0].getAttribute("radius"))||0,J=parseFloat(y.children[0].getAttribute("length"))||0;k.scale.set(H,J,H),k.rotation.set(Math.PI/2,0,0),D.add(k)}}else if(S==="origin"){const U=bi(y.getAttribute("xyz")),k=bi(y.getAttribute("rpy"));D.position.set(U[0],U[1],U[2]),D.rotation.set(0,0,0),Gh(D,k)}}),D}return f(t)}defaultMeshLoader(t,e,n){/\.stl$/i.test(t)?new Hv(e).load(t,r=>{const a=new me(r,new Ms);n(a)},null,r=>n(null,r)):/\.dae$/i.test(t)?new Gv(e).load(t,r=>n(r.scene),null,r=>n(null,r)):console.warn(`URDFLoader: Could not load model at ${t}.
No loader available`)}}const Ba=8,$v=.002;function za(i,t){return Math.hypot(t.clientX-i.startX,t.clientY-i.startY)}class Kv{constructor(t){se(this,"interaction",null);se(this,"onPointerDown",t=>{const{canvas:e,layer:n}=this.options,s=this.options.getSession();if(!s||this.options.isBusy()||!t.isPrimary||t.button!==0||s.read_only||s.generation.status==="running")return;const r=this.options.getSelectedHandle(),a=n.pickRestoreGhost(t,r);if(a){this.options.selectHandle(a),this.interaction={kind:"restore",pointerId:t.pointerId,handle:a,startX:t.clientX,startY:t.clientY},this.options.controls.enabled=!1,e.style.cursor="pointer",this.setState("restore-armed"),this.capturePointer(t.pointerId);return}const o=n.pickHandle(t,(s==null?void 0:s.edit_handles)??[],r);if(this.setState(o?"handle-hit":"miss"),!o)return;if((r==null?void 0:r.handle_id)!==o.handle_id){this.options.selectHandle(o),this.setState("selected");return}const c=s==null?void 0:s.surfaces.find(u=>u.surface_id===o.surface_id);if(!c){this.setState("surface-missing");return}const l=new ii().setFromNormalAndCoplanarPoint(new L(...c.normal).normalize(),new L(...c.origin)),h=new L;if(!n.intersectPointerPlane(t,l,h)){this.setState("plane-miss");return}this.interaction={kind:"drag",pointerId:t.pointerId,handle:o,startX:t.clientX,startY:t.clientY,plane:l,offset:new L(...o.world_position).sub(h),preview:null,dragging:!1},this.options.controls.enabled=!1,e.style.cursor="grab",this.setState("armed"),this.capturePointer(t.pointerId)});se(this,"onPointerMove",t=>{var a,o;const{canvas:e,layer:n}=this.options,s=this.interaction;if(!s){if(this.options.isBusy()||(a=this.options.getSession())!=null&&a.read_only){e.style.cursor="default";return}const c=this.options.getSelectedHandle();e.style.cursor=n.pickRestoreGhost(t,c)?"pointer":n.pickHandle(t,((o=this.options.getSession())==null?void 0:o.edit_handles)??[],c)?"grab":"default";return}if(t.pointerId!==s.pointerId)return;if(s.kind==="restore"){this.setState(za(s,t)>=Ba?"restore-cancelled":"restore-armed");return}if(!s.dragging&&za(s,t)<Ba)return;s.dragging=!0,e.style.cursor="grabbing",this.setState("dragging");const r=new L;n.intersectPointerPlane(t,s.plane,r)&&(s.preview=r.add(s.offset),n.previewPosition(s.handle,s.preview),this.options.updatePositionOffset(s.handle,s.preview),this.setState("preview"))});se(this,"onPointerUp",async t=>{const e=this.interaction;if(!e||t.pointerId!==e.pointerId)return;if(this.interaction=null,this.options.controls.enabled=!0,this.options.canvas.style.cursor="default",this.releasePointer(t.pointerId),e.kind==="restore"){if(za(e,t)>=Ba){this.setState("restore-cancelled");return}this.setState("restoring"),this.setState(await this.options.restoreHandle(e.handle)?"restored":"error");return}if(!e.dragging||!e.preview){this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.setState("selected");return}const n=e.preview.clone();if(n.distanceTo(new L(...e.handle.world_position))<$v){this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.setState("no-op");return}this.setState("submitting");const s=await this.options.moveHandle(e.handle,n);this.setState(s?"moved":"error"),s||(this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.options.rebuildHandles())});this.options=t;const{canvas:e}=t;e.addEventListener("pointerdown",this.onPointerDown),e.addEventListener("pointermove",this.onPointerMove),e.addEventListener("pointerup",this.onPointerUp),e.addEventListener("pointercancel",()=>this.cancel()),e.addEventListener("pointerleave",()=>{this.interaction&&this.cancel()})}get active(){return this.interaction!==null}cancel(t="cancelled"){const e=this.interaction;(e==null?void 0:e.kind)==="drag"&&(this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle)),this.interaction=null,this.options.controls.enabled=!0,this.options.canvas.style.cursor="default",this.setState(t),e&&this.releasePointer(e.pointerId)}setState(t){this.options.canvas.dataset.dragState=t}capturePointer(t){try{this.options.canvas.setPointerCapture(t)}catch{}}releasePointer(t){try{this.options.canvas.hasPointerCapture(t)&&this.options.canvas.releasePointerCapture(t)}catch{}}}function er(i){const t=new Set,e=new Set,n=new Set;i.traverse(s=>{const r=s;r.geometry&&!(s.parent instanceof ji)&&t.add(r.geometry),(Array.isArray(r.material)?r.material:r.material?[r.material]:[]).forEach(o=>e.add(o))}),e.forEach(s=>{Object.values(s).forEach(r=>{r instanceof Ye&&n.add(r)}),s.dispose()}),n.forEach(s=>s.dispose()),t.forEach(s=>s.dispose())}function zn(i){er(i),i.clear()}const Wh=.008,Jv=.006,Xh=14,Zv=10;class Qv{constructor(t,e){se(this,"handles",new Fe);se(this,"restoreGhosts",new Fe);se(this,"handleObjects",new Map);se(this,"restoreGhostObjects",new Map);se(this,"handleHitMeshes",[]);se(this,"restoreGhostHitMeshes",[]);se(this,"pointer",new At);se(this,"raycaster",new yv);se(this,"signature","");this.canvas=t,this.camera=e}clear(){zn(this.handles),zn(this.restoreGhosts),this.signature="",this.handleObjects.clear(),this.restoreGhostObjects.clear(),this.handleHitMeshes.length=0,this.restoreGhostHitMeshes.length=0,this.canvas.dataset.restoreGhostCount="0"}setVisible(t){this.handles.visible=t,this.restoreGhosts.visible=t}rebuild({handles:t,visibleHandleIds:e,selectedHandle:n,radius:s}){const r=t.filter(o=>e.has(o.handle_id)||o.handle_id===(n==null?void 0:n.handle_id)),a=JSON.stringify([s,n==null?void 0:n.handle_id,r]);if(a!==this.signature){this.clear(),this.signature=a,this.canvas.dataset.contactMarker="episode-handle";for(const o of t){if(!e.has(o.handle_id)&&o.handle_id!==(n==null?void 0:n.handle_id))continue;const c=o.handle_id===(n==null?void 0:n.handle_id),l=new L(...o.surface_normal).normalize(),h=new L(...o.surface_tangent_u).normalize(),u=new L(...o.surface_tangent_v).normalize(),f=new Fe;f.quaternion.setFromRotationMatrix(new jt().makeBasis(h,u,l)),f.position.set(...o.world_position).addScaledVector(l,Wh);const p=String(o.metadata.surface_editor_status||"bound"),g=c?16768370:p==="edited"?6543004:15134195,_=new me(new wo(s*.48,s,32),new je({color:g,transparent:!0,opacity:c?1:.82,side:un,depthTest:!1,depthWrite:!1}));_.renderOrder=8,f.add(_);const m=new me(new Eo(s*.25,24),new je({color:g,side:un,depthTest:!1,depthWrite:!1}));m.position.z=.001,m.renderOrder=9,f.add(m);const d=new me(new li(s*.82,16,10),new je({transparent:!0,opacity:0,depthWrite:!1}));d.userData.handle=o,f.add(d),this.handleHitMeshes.push(d),c&&this.addSelectionAxes(f,s),this.handles.add(f),this.handleObjects.set(o.handle_id,f),o.has_position_offset&&this.addRestoreGhost(o,f,l,s)}this.canvas.dataset.restoreGhostCount=String(this.restoreGhostObjects.size)}}pickRestoreGhost(t,e){if(!this.restoreGhosts.visible)return null;this.setPointerRay(t);const n=this.raycaster.intersectObjects(this.restoreGhostHitMeshes,!1)[0];if(n)return n.object.userData.restoreHandle;if(!(e!=null&&e.has_position_offset))return null;const s=this.canvas.getBoundingClientRect(),r=Number(this.canvas.dataset.selectedRestoreGhostX)*s.width,a=Number(this.canvas.dataset.selectedRestoreGhostY)*s.height,o=t.clientX-s.left,c=t.clientY-s.top;return Number.isFinite(r)&&Number.isFinite(a)&&Math.hypot(r-o,a-c)<=Zv?e:null}pickHandle(t,e,n){if(!this.handles.visible)return null;this.setPointerRay(t);const s=this.canvas.getBoundingClientRect(),r=t.clientX-s.left,a=t.clientY-s.top,o=this.raycaster.intersectObjects(this.handleHitMeshes,!1),c=o.find(u=>u.object.userData.handle.handle_id===(n==null?void 0:n.handle_id));if(c)return c.object.userData.handle;if(n){const u=Number(this.canvas.dataset.selectedHandleX)*s.width,f=Number(this.canvas.dataset.selectedHandleY)*s.height;if(Number.isFinite(u)&&Number.isFinite(f)&&Math.hypot(u-r,f-a)<=Xh)return n}if(o[0])return o[0].object.userData.handle;let l=null,h=Xh;for(const u of e){const f=this.handleObjects.get(u.handle_id);if(!f)continue;const p=f.getWorldPosition(new L).project(this.camera);if(p.z<-1||p.z>1)continue;const g=(p.x+1)*.5*s.width,_=(1-p.y)*.5*s.height,m=Math.hypot(g-r,_-a);m<=h&&(l=u,h=m)}return l}intersectPointerPlane(t,e,n){return this.setPointerRay(t),this.raycaster.ray.intersectPlane(e,n)!==null}previewPosition(t,e){const n=this.handleObjects.get(t.handle_id);n&&n.position.copy(e).addScaledVector(new L(...t.surface_normal),Wh)}restorePosition(t){this.previewPosition(t,new L(...t.world_position))}updateProjection(t){const e=t?this.handleObjects.get(t.handle_id):null,n=t?this.restoreGhostObjects.get(t.handle_id):null;if(n){const r=n.getWorldPosition(new L).project(this.camera);this.canvas.dataset.selectedRestoreGhostX=String((r.x+1)/2),this.canvas.dataset.selectedRestoreGhostY=String((1-r.y)/2)}else delete this.canvas.dataset.selectedRestoreGhostX,delete this.canvas.dataset.selectedRestoreGhostY;if(!e){delete this.canvas.dataset.selectedHandleX,delete this.canvas.dataset.selectedHandleY,delete this.canvas.dataset.selectedHandleId;return}const s=e.getWorldPosition(new L).project(this.camera);this.canvas.dataset.selectedHandleX=String((s.x+1)/2),this.canvas.dataset.selectedHandleY=String((1-s.y)/2),this.canvas.dataset.selectedHandleId=t.handle_id}setPointerRay(t){const e=this.canvas.getBoundingClientRect();this.pointer.x=(t.clientX-e.left)/e.width*2-1,this.pointer.y=-((t.clientY-e.top)/e.height)*2+1,this.raycaster.setFromCamera(this.pointer,this.camera)}addSelectionAxes(t,e){const n=e*1.85,s=new ji(new L(1,0,0),new L,n,15754313,e*.42,e*.22),r=new ji(new L(0,1,0),new L,n,6869905,e*.42,e*.22);for(const a of[s.line,s.cone,r.line,r.cone])(Array.isArray(a.material)?a.material:[a.material]).forEach(c=>{c.depthTest=!1,c.depthWrite=!1});t.add(s,r)}addRestoreGhost(t,e,n,s){const r=new Fe;r.quaternion.copy(e.quaternion),r.position.set(...t.initial_world_position).addScaledVector(n,Jv);const a={color:10136505,transparent:!0,side:un,depthTest:!1,depthWrite:!1},o=new me(new wo(s*.5,s*.92,32),new je({...a,opacity:.24}));o.renderOrder=7,r.add(o);const c=new me(new Eo(s*.16,20),new je({...a,opacity:.2}));c.position.z=.001,c.renderOrder=7,r.add(c);const l=new me(new li(s*.78,14,8),new je({transparent:!0,opacity:0,depthWrite:!1}));l.userData.restoreHandle=t,r.add(l),this.restoreGhostHitMeshes.push(l),this.restoreGhosts.add(r),this.restoreGhostObjects.set(t.handle_id,r)}}const tx=1e-6;function ex(i,t){const e=((t==null?void 0:t.clone())??new L(...i.world_position)).sub(new L(...i.initial_world_position));return{u:e.dot(new L(...i.surface_tangent_u)),v:e.dot(new L(...i.surface_tangent_v))}}function qh(i){const t=Math.abs(i)<5e-7?0:i;return`${t>=0?"+":""}${t.toFixed(3)} m`}class zu extends Error{constructor(t,e){super(e),this.status=t}}async function An(i,t){const e=await fetch(i,{headers:{"Content-Type":"application/json"},...t});if(!e.ok){const n=await e.json().catch(()=>({})),s=Array.isArray(n.detail)?n.detail.map(r=>{var a;return`${((a=r.loc)==null?void 0:a.join("."))||"Request"}: ${r.msg||"Invalid value"}`}).join(`
`):typeof n.detail=="string"?n.detail:e.statusText;throw new zu(e.status,s||`HTTP ${e.status}`)}return e.json()}const nx={left_foot:["LHEE","LTOE"],right_foot:["RHEE","RTOE"],left_hand:["LH"],right_hand:["RH"],left_knee:["LK"],right_knee:["RK"]};function Vu(i,t=8){const e=i.getBoundingClientRect(),n=Math.max(1,t),s=e.width<560?54:68,r=28;return{width:e.width,height:e.height,labelW:s,rulerH:r,rowH:Math.max(1,(e.height-r)/n),plotW:Math.max(1,e.width-s),rows:n}}function zi(i,t,e){return t.labelW+i/Math.max(1,e-1)*t.plotW}function ix(i,t,e){const n=Math.max(0,Math.min(1,(i-t.labelW)/t.plotW));return Math.round(n*Math.max(0,e-1))}function sx(i){const t=10**Math.floor(Math.log10(Math.max(i,1e-6))),e=i/t;return(e<=1?1:e<=2?2:e<=5?5:10)*t}function Hu(i){const t=Math.floor(i/60),e=i-t*60;return t?`${t}:${e.toFixed(e<10?1:0).padStart(e<10?4:2,"0")}`:`${e.toFixed(e<10?1:0)}s`}function rx(i){var m;const{canvas:t,session:e,frame:n,selectedHandle:s,stableCuts:r,partColors:a}=i,o=Vu(t,(e==null?void 0:e.contact_force.part_order.length)??8),c=t.getContext("2d");if(!c)return;const l=Math.min(window.devicePixelRatio,2);if(t.width=Math.max(1,Math.round(o.width*l)),t.height=Math.max(1,Math.round(o.height*l)),c.setTransform(l,0,0,l,0,0),c.clearRect(0,0,o.width,o.height),c.fillStyle="#0b1117",c.fillRect(0,0,o.width,o.height),!e)return;const h=e.qpos.length;c.fillStyle="#0d141b",c.fillRect(0,0,o.labelW,o.height),c.fillStyle="#111923",c.fillRect(o.labelW,0,o.plotW,o.rulerH);for(let d=0;d<o.rows;d++){const w=o.rulerH+d*o.rowH;c.fillStyle=d%2===0?"#121a22":"#0f171f",c.fillRect(o.labelW,w,o.plotW,o.rowH),c.strokeStyle="#22303c",c.beginPath(),c.moveTo(0,Math.round(w)+.5),c.lineTo(o.width,Math.round(w)+.5),c.stroke(),c.fillStyle=`#${a[d%a.length].toString(16).padStart(6,"0")}`,c.fillRect(8,w+o.rowH/2-3,6,6),c.fillStyle="#aebbc7",c.font="600 10px ui-monospace,monospace",c.textBaseline="middle",c.fillText(e.contact_force.part_order[d]||"",20,w+o.rowH/2)}const u=Math.max(1,h-1)/e.fps,f=sx(u/Math.max(2,Math.floor(o.plotW/92))),p=Math.max(1,Math.round(f*e.fps)),g=Math.max(1,Math.round(p/5));for(let d=0;d<h;d+=g){const w=Math.round(zi(d,o,h))+.5,T=d%p===0;c.strokeStyle=T?"#344451":"#1d2a34",c.globalAlpha=T?.9:.65,c.beginPath(),c.moveTo(w,T?o.rulerH-7:o.rulerH-4),c.lineTo(w,o.height),c.stroke(),c.globalAlpha=1,T&&(c.fillStyle="#aeb5bd",c.font="10px ui-monospace,monospace",c.fillText(Hu(d/e.fps),Math.min(w+4,o.width-38),10),c.fillStyle="#6f7780",c.font="9px ui-monospace,monospace",c.fillText(String(d),Math.min(w+4,o.width-32),21))}c.fillStyle="#7e8790",c.font="9px ui-monospace,monospace",c.fillText("TIME",8,9),c.fillText("FRAME",8,21);for(let d=0;d<o.rows;d++){let w=-1;for(let T=0;T<=h;T++){const M=T<h&&!!((m=e.contact_force.masks[T])!=null&&m[d]);if(M&&w<0&&(w=T),!M&&w>=0){const F=zi(w,o,h),P=zi(Math.max(w,T-1),o,h)+Math.max(1,o.plotW/h);c.fillStyle=`#${a[d%a.length].toString(16).padStart(6,"0")}`,c.globalAlpha=.78,c.beginPath(),c.roundRect(F,o.rulerH+d*o.rowH+3,Math.max(2,P-F),Math.max(2,o.rowH-6),2),c.fill(),c.globalAlpha=1,w=-1}}}if(s){const d=nx[s.body]||[s.body],w=zi(s.start_frame,o,h),T=zi(Math.max(s.start_frame,s.end_frame-1),o,h);for(const M of d){const F=e.contact_force.part_order.indexOf(M);F<0||(c.strokeStyle="#b7fff1",c.lineWidth=1.5,c.strokeRect(w+.5,o.rulerH+F*o.rowH+2.5,Math.max(3,T-w),Math.max(3,o.rowH-5)),c.lineWidth=1)}}c.setLineDash([3,3]);for(const d of r){const w=Math.round(zi(d,o,h))+.5;c.strokeStyle="#d9b96e",c.globalAlpha=.38,c.beginPath(),c.moveTo(w,o.rulerH),c.lineTo(w,o.height),c.stroke()}c.setLineDash([]),c.globalAlpha=1;const _=Math.round(zi(n,o,h))+.5;c.strokeStyle="#72ead3",c.lineWidth=1.5,c.beginPath(),c.moveTo(_,0),c.lineTo(_,o.height),c.stroke(),c.fillStyle="#72ead3",c.beginPath(),c.moveTo(_-5,0),c.lineTo(_+5,0),c.lineTo(_,7),c.closePath(),c.fill(),c.lineWidth=1}/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Gu=(i,t,e=[])=>{const n=document.createElementNS("http://www.w3.org/2000/svg",i);return Object.keys(t).forEach(s=>{n.setAttribute(s,String(t[s]))}),e.length&&e.forEach(s=>{const r=Gu(...s);n.appendChild(r)}),n};var ox=([i,t,e])=>Gu(i,t,e);/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ax=i=>Array.from(i.attributes).reduce((t,e)=>(t[e.name]=e.value,t),{}),cx=i=>typeof i=="string"?i:!i||!i.class?"":i.class&&typeof i.class=="string"?i.class.split(" "):i.class&&Array.isArray(i.class)?i.class:"",lx=i=>i.flatMap(cx).map(e=>e.trim()).filter(Boolean).filter((e,n,s)=>s.indexOf(e)===n).join(" "),hx=i=>i.replace(/(\w)(\w*)(_|-|\s*)/g,(t,e,n)=>e.toUpperCase()+n.toLowerCase()),jh=(i,{nameAttr:t,icons:e,attrs:n})=>{var g;const s=i.getAttribute(t);if(s==null)return;const r=hx(s),a=e[r];if(!a)return console.warn(`${i.outerHTML} icon name was not found in the provided icons object.`);const o=ax(i),[c,l,h]=a,u={...l,"data-lucide":s,...n,...o},f=lx(["lucide",`lucide-${s}`,o,n]);f&&Object.assign(u,{class:f});const p=ox([c,u,h]);return(g=i.parentNode)==null?void 0:g.replaceChild(p,i)};/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ue={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"};/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const ux=["svg",Ue,[["path",{d:"M12 5v14"}],["path",{d:"m19 12-7 7-7-7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const dx=["svg",Ue,[["path",{d:"m12 19-7-7 7-7"}],["path",{d:"M19 12H5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const fx=["svg",Ue,[["path",{d:"M5 12h14"}],["path",{d:"m12 5 7 7-7 7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const px=["svg",Ue,[["path",{d:"m5 12 7-7 7 7"}],["path",{d:"M12 19V5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const mx=["svg",Ue,[["path",{d:"M20 6 9 17l-5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const gx=["svg",Ue,[["path",{d:"m15 18-6-6 6-6"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const _x=["svg",Ue,[["path",{d:"m9 18 6-6-6-6"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const vx=["svg",Ue,[["path",{d:"m11 17-5-5 5-5"}],["path",{d:"m18 17-5-5 5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const xx=["svg",Ue,[["path",{d:"m6 17 5-5-5-5"}],["path",{d:"m13 17 5-5-5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const yx=["svg",Ue,[["circle",{cx:"12",cy:"12",r:"3"}],["path",{d:"M3 7V5a2 2 0 0 1 2-2h2"}],["path",{d:"M17 3h2a2 2 0 0 1 2 2v2"}],["path",{d:"M21 17v2a2 2 0 0 1-2 2h-2"}],["path",{d:"M7 21H5a2 2 0 0 1-2-2v-2"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Mx=["svg",Ue,[["path",{d:"m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Sx=["svg",Ue,[["path",{d:"M21 12a9 9 0 1 1-6.219-8.56"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const bx=["svg",Ue,[["rect",{x:"14",y:"4",width:"4",height:"16",rx:"1"}],["rect",{x:"6",y:"4",width:"4",height:"16",rx:"1"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ex=["svg",Ue,[["polygon",{points:"6 3 20 12 6 21 6 3"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const wx=["svg",Ue,[["path",{d:"m15 14 5-5-5-5"}],["path",{d:"M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Tx=["svg",Ue,[["path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"}],["path",{d:"M21 3v5h-5"}],["path",{d:"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"}],["path",{d:"M8 16H3v5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ax=["svg",Ue,[["path",{d:"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"}],["path",{d:"M3 3v5h5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Cx=["svg",Ue,[["path",{d:"M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"}],["path",{d:"M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"}],["path",{d:"M7 3v4a1 1 0 0 0 1 1h7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Rx=["svg",Ue,[["line",{x1:"18",x2:"18",y1:"20",y2:"4"}],["polygon",{points:"14,20 4,12 14,4"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Px=["svg",Ue,[["line",{x1:"6",x2:"6",y1:"4",y2:"20"}],["polygon",{points:"10,4 20,12 10,20"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Lx=["svg",Ue,[["path",{d:"M3 6h18"}],["path",{d:"M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"}],["path",{d:"M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"}],["line",{x1:"10",x2:"10",y1:"11",y2:"17"}],["line",{x1:"14",x2:"14",y1:"11",y2:"17"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Nx=["svg",Ue,[["path",{d:"M9 14 4 9l5-5"}],["path",{d:"M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Dx=["svg",Ue,[["path",{d:"m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"}],["path",{d:"m14 7 3 3"}],["path",{d:"M5 6v4"}],["path",{d:"M19 14v4"}],["path",{d:"M10 2v2"}],["path",{d:"M7 8H3"}],["path",{d:"M21 16h-4"}],["path",{d:"M11 3H9"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ix=({icons:i={},nameAttr:t="data-lucide",attrs:e={}}={})=>{if(!Object.values(i).length)throw new Error(`Please provide an icons object.
If you want to use all the icons you can import it like:
 \`import { createIcons, icons } from 'lucide';
lucide.createIcons({icons});\``);if(typeof document>"u")throw new Error("`createIcons()` only works in a browser environment.");const n=document.querySelectorAll(`[${t}]`);if(Array.from(n).forEach(s=>jh(s,{nameAttr:t,icons:i,attrs:e})),t==="data-lucide"){const s=document.querySelectorAll("[icon-name]");s.length>0&&(console.warn("[Lucide] Some icons were found with the now deprecated icon-name attribute. These will still be replaced for backwards compatibility, but will no longer be supported in v1.0 and you should switch to data-lucide"),Array.from(s).forEach(r=>jh(r,{nameAttr:"icon-name",icons:i,attrs:e})))}},Ux=()=>`
  <header class="topbar">
    <div class="brand"><div><strong>Motion Edit</strong><span id="motionLabel">No motion</span></div></div>
    <div class="top-actions">
      <button class="icon" id="openMotionBtn" title="Open registered motion" aria-label="Open registered motion"><i data-lucide="folder-open"></i></button>
      <button class="icon" id="focusBtn" title="Frame scene"><i data-lucide="focus"></i></button>
      <button class="icon" id="undoBtn" title="Undo"><i data-lucide="undo-2"></i></button>
      <button class="icon" id="redoBtn" title="Redo"><i data-lucide="redo-2"></i></button>
      <button class="icon primary" id="saveBtn" title="Save contact edit plan"><i data-lucide="save"></i></button>
    </div>
  </header>`,Fx=()=>`
  <section class="viewport">
    <canvas id="scene"></canvas>
    <div class="viewport-hud"><strong id="viewportMotion">No motion loaded</strong><span id="viewportFrame">Frame 0</span><span id="viewportTime">0.00 s</span></div>
    <div class="shortcut-hint"><span>Space</span> Play <span>← →</span> Frame <span>[ ]</span> Contact</div>
    <div id="sceneStatus" class="scene-status">Select a motion asset</div>
    <button id="retryLoad" class="retry-load" hidden>Retry loading</button>
  </section>`,Ox=()=>`
  <div class="tab-page active" data-page="contact">
    <div class="page-heading"><strong>Contacts</strong><div class="heading-stats"><span id="anchorCount">0 handles</span><span id="editCount">0 edits</span></div></div>
    <section id="reviewPanel" hidden></section>
    <p id="playbackNotice" class="playback-notice" hidden>只读轨迹：接触状态以已验证的 Newton 数据为准；无接触层时不显示编辑手柄。</p>
    <div id="selection" class="selection empty">None</div>
    <div class="position-offset disabled" id="positionOffset">
      <div class="panel-title">Position offset</div>
      <dl><div><dt>Δu</dt><dd id="offsetU">—</dd></div><div><dt>Δv</dt><dd id="offsetV">—</dd></div></dl>
    </div>
    <div class="anchor-browser">
      <div class="browser-heading">Browse contact episodes</div>
      <div class="anchor-nav"><button class="nav-command" id="prevAnchor" title="Previous matching contact"><i data-lucide="chevron-left"></i><span>Previous</span></button><button class="nav-command" id="nextAnchor" title="Next matching contact"><span>Next</span><i data-lucide="chevron-right"></i></button></div>
      <div class="filter-grid"><input id="anchorSearch" placeholder="Filter body, surface, id" /><select id="statusFilter"><option value="all">All status</option><option value="bound">Bound</option><option value="edited">Edited</option><option value="clamped">Clamped</option><option value="suspicious">Suspicious</option><option value="failed">Failed</option><option value="unbound">Unbound</option></select></div>
      <div class="browse-options"><label class="toggle"><input id="currentOnly" type="checkbox" checked /><span>Current frame only</span></label><label class="field"><span>Boundary</span><select id="modeSelect"><option value="reject">Reject</option><option value="clamp">Clamp</option></select></label></div>
    </div>
  </div>`,kx=()=>`
  <div class="tab-page" data-page="display">
    <div class="page-heading"><strong>Display</strong></div>
    <section class="display-section"><div class="section-heading">Scene</div><div class="layer-list">
      <label class="toggle"><input id="terrainToggle" type="checkbox" checked /><span>Terrain mesh</span></label><label class="toggle"><input id="surfaceToggle" type="checkbox" /><span>Contact surfaces</span></label><label class="toggle"><input id="contactSampleToggle" type="checkbox" checked /><span>Contact point + force</span></label><label class="toggle"><input id="handleToggle" type="checkbox" checked /><span>Edit handles</span></label><label class="toggle"><input id="rootPathToggle" type="checkbox" /><span>Root path</span></label><label class="toggle"><input id="guideToggle" type="checkbox" checked /><span>Selection guides</span></label>
    </div></section>
    <section class="display-section"><div class="section-heading">Appearance</div><label class="slider-field"><span>Handle size</span><input id="handleSize" type="range" min="70" max="180" value="110" /></label><label class="slider-field"><span>Force scale</span><input id="forceScale" type="range" min="25" max="300" value="100" /></label></section>
    <section class="display-section"><div class="section-heading">Channels</div><div id="partLegend" class="part-legend"></div></section>
  </div>`,Bx=()=>`
  <div class="tab-page" data-page="output">
    <div class="page-heading"><strong>Output</strong></div>
    <div id="generationStatus" class="generation-status idle"><strong>Ready</strong><span>Candidate · native validation required</span></div>
    <div id="planStatus" class="plan-status">No plan saved</div>
    <div class="pipeline-actions"><button id="validateBtn" class="secondary-command"><i data-lucide="check"></i><span>Validate</span></button><button id="generateBtn" class="generate-command"><i data-lucide="wand-sparkles"></i><span>Generate</span></button></div>
    <details class="output-settings"><summary>Advanced settings</summary><label class="stack-field"><span>Edit plan</span><input id="planPath" /></label><label class="stack-field"><span>Generated motion</span><input id="outputMotion" /></label><label class="stack-field"><span>Edited contact draft</span><input id="outputLayer" /></label><label class="stack-field"><span>Motion ID</span><input id="outputMotionId" /></label><label class="toggle"><input id="registerMotion" type="checkbox" checked /><span>Register motion</span></label><label class="toggle"><input id="overwriteOutput" type="checkbox" /><span>Replace existing output</span></label></details>
    <div class="source-reference"><span>Source contact layer</span><code id="sourceLayer"></code></div>
    <div class="session-actions"><button id="reloadBtn"><i data-lucide="refresh-cw"></i><span>Reload</span></button><button id="discardBtn"><i data-lucide="trash-2"></i><span>Discard edits</span></button></div>
  </div>`,zx=()=>`
  <aside class="inspector">
    <div class="inspector-tabs"><button data-tab="contact" class="active">Contact</button><button data-tab="display">Display</button><button data-tab="output">Output</button></div>
    <div class="inspector-pages">${Ox()}${kx()}${Bx()}</div>
    <section class="recent-motion-dock" aria-label="Motions opened this session"><div class="recent-motion-head"><span>This session</span><small id="recentMotionCount">0</small></div><div id="recentMotionList" class="recent-motion-list"></div><details><summary>打开只读回放／实验报告</summary><input id="reviewPath" placeholder="项目内 NPZ / JSON 路径" /><input id="reviewTerrain" placeholder="地形 OBJ 路径（可选）" /><button id="reviewOpen">打开</button></details></section>
  </aside>`,Vx=()=>`
  <section class="timeline-panel">
    <div id="timelineResizer" class="timeline-resizer" title="Drag to resize timeline"><span></span></div>
    <div class="transport"><div class="toolbar-group cut-nav"><button class="icon" id="prevCut" title="Previous stable cut"><i data-lucide="chevrons-left"></i></button><button class="icon" id="nextCut" title="Next stable cut"><i data-lucide="chevrons-right"></i></button></div><div class="transport-main"><div class="toolbar-group playback-nav"><button class="icon" id="prevBtn" title="Previous frame"><i data-lucide="step-back"></i></button><button class="icon play" id="playBtn" title="Play or pause"><i data-lucide="play"></i></button><button class="icon" id="nextBtn" title="Next frame"><i data-lucide="step-forward"></i></button></div><div class="frame-readout"><input id="frameInput" class="frame-input" type="number" min="0" value="0" /><span id="frameTotal">/ 0</span></div></div><label class="fps">FPS <input id="fpsInput" type="number" min="1" max="240" value="50" /></label></div>
    <div class="timeline-wrap"><canvas id="timeline" aria-label="Contact timeline"></canvas><div id="timelineHover" class="timeline-hover hidden"></div></div>
  </section>`;function Hx(i){const t=document.createElement("template");t.innerHTML=`${Ux()}<main class="workspace">${Fx()}${zx()}${Vx()}</main>
    <dialog id="motionPicker" aria-labelledby="motionPickerTitle"><div class="motion-picker-head"><strong id="motionPickerTitle">打开已注册轨迹</strong><button id="closeMotionPicker" aria-label="Close motion picker">关闭</button></div><label for="motionSearch">搜索名称或 ID</label><input id="motionSearch" type="search" autocomplete="off" placeholder="搜索轨迹" /><div id="motionPickerList"></div></dialog>`,i.replaceChildren(t.content.cloneNode(!0)),tl()}function tl(){Ix({icons:{Play:Ex,Pause:bx,StepBack:Rx,StepForward:Px,Undo2:Nx,Redo2:wx,Save:Cx,RotateCcw:Ax,Focus:yx,FolderOpen:Mx,RefreshCw:Tx,Check:mx,ChevronLeft:gx,ChevronRight:_x,ChevronsLeft:vx,ChevronsRight:xx,ArrowLeft:dx,ArrowRight:fx,ArrowUp:px,ArrowDown:ux,Trash2:Lx,WandSparkles:Dx,LoaderCircle:Sx}})}function et(i){const t=document.getElementById(i);if(!t)throw new Error(`missing UI element #${i}`);return t}function Gx(){const i=[...document.querySelectorAll("[data-tab]")],t=[...document.querySelectorAll("[data-page]")];for(const e of i)e.addEventListener("click",()=>{const n=e.dataset.tab;for(const s of i)s.classList.toggle("active",s===e);for(const s of t)s.classList.toggle("active",s.dataset.page===n)})}class Wx{constructor(t,e){se(this,"group",new Fe);se(this,"annotations",new Fe);se(this,"reference",null);se(this,"current",null);se(this,"review");se(this,"selected");se(this,"spacing",1);se(this,"link","left_ankle_roll_link");se(this,"normals",!0);se(this,"displacement",!0);se(this,"scale",3);se(this,"panel");se(this,"details");se(this,"terrain",null);se(this,"opacity",.45);this.scene=t,this.onPose=e,this.panel=document.getElementById("reviewPanel"),this.details=document.createElement("pre"),this.details.style.whiteSpace="pre-wrap",this.scene.add(this.group,this.annotations)}clearAnnotations(){zn(this.annotations)}setup(t,e,n,s){var M,F;if(this.group.clear(),this.clearAnnotations(),this.panel.replaceChildren(),this.review=t,this.terrain=n,this.current=e,this.reference=null,this.selected=void 0,this.panel.hidden=!t,!t||t.kind==="support_motion"||t.kind==="support_slip")return;const r=document.createElement("p");if(r.textContent=t.notice,this.panel.append(r),t.kind!=="report"||!((M=t.records)!=null&&M.length))return;const a=t.records,o=a.find(P=>P.label===t.reference)||a[0];this.reference=e.clone(),this.spacing=n?Math.max(1,new Xn().setFromObject(n).getSize(new L).y/2+.5):1;const c=o.q;if(this.reference.position.set(c[0],c[1]-this.spacing,c[2]),this.reference.quaternion.set(c[4],c[5],c[6],c[3]),s.forEach((P,N)=>this.reference.setJointValue(P,c[7+N])),this.group.add(this.reference),n){const P=n.clone();P.position.y-=this.spacing,this.group.add(P),n.position.y+=this.spacing}const l=document.createElement("p");l.textContent="左：原始姿态　右：选中结果",this.panel.append(l);const h=document.createElement("select"),u=document.createElement("select");h.setAttribute("aria-label","实验方法"),h.id="reviewMethod",u.setAttribute("aria-label","保存的迭代"),u.id="reviewIteration",[...new Set(a.map(P=>P.method))].forEach(P=>h.add(new Option(P,P)));const f=()=>{this.selected=a.find(P=>P.label===u.value),this.onPose(this.selected.q)},p=()=>{u.replaceChildren();const P=a.filter(D=>D.method===h.value),N=D=>D.iteration==="initial"?-1:D.iteration==="final"?1/0:Number(D.iteration.replace("step",""))||0;P.sort((D,y)=>N(D)-N(y)),P.forEach(D=>u.add(new Option(D.iteration,D.label))),u.value=(P.find(D=>D.iteration==="final")||P[0]).label,f()};h.onchange=p,u.onchange=f;const g=(P,N)=>{const D=document.createElement("label");D.className="stack-field";const y=document.createElement("span");y.textContent=P,D.append(y,N),this.panel.append(D)};g("实验方法",h),g("保存的迭代",u);const _=document.createElement("select");_.id="reviewLink",_.setAttribute("aria-label","位移部位"),Object.keys(e.links).forEach(P=>_.add(new Option(P,P))),_.value=e.links[this.link]?this.link:Object.keys(e.links)[0],this.link=_.value,_.onchange=()=>{this.link=_.value,this.onPose(this.selected.q)},g("位移部位",_);const m=(P,N,D)=>{const y=document.createElement("label");y.className="toggle";const S=document.createElement("input");S.type="checkbox",S.checked=N,S.onchange=()=>{D(S.checked),this.onPose(this.selected.q)},y.append(S,document.createTextNode(P)),this.panel.append(y)};m("穿透法线（报告记录）",this.normals,P=>this.normals=P),m("材料点实际位移 dx",this.displacement,P=>this.displacement=P);const d=document.createElement("input");d.type="range",d.min="1",d.max="20",d.value=String(this.scale),d.setAttribute("aria-label","位移显示倍率"),d.oninput=()=>{this.scale=Number(d.value),this.onPose(this.selected.q)},g("位移显示倍率",d);const w=document.createElement("input");w.type="range",w.min=".05",w.max="1",w.step=".05",w.value=String(this.opacity);const T=()=>{this.opacity=Number(w.value),[this.terrain,...this.group.children.filter(P=>P!==this.reference)].forEach(P=>P==null?void 0:P.traverse(N=>{N.isMesh&&(N.material.transparent=this.opacity<1,N.material.opacity=this.opacity,N.material.depthWrite=this.opacity===1)}))};w.oninput=T,T(),g("地形透明度",w),this.panel.append(this.details),h.value=((F=a.find(P=>P.label!==o.label))==null?void 0:F.method)||o.method,p()}update(){var l;if(!this.reference||!this.current||!this.selected||!((l=this.review)!=null&&l.records))return;this.current.position.y+=this.spacing,this.current.updateMatrixWorld(!0),this.reference.updateMatrixWorld(!0),this.clearAnnotations();const t=this.review.records.find(h=>h.label===this.review.reference)||this.review.records[0];[t,this.selected].forEach((h,u)=>{const f=u===0?-this.spacing:this.spacing;this.normals&&h.normal_starts.forEach((_,m)=>{const d=new L(...h.normals[m]);d.length()>0&&this.annotations.add(new ji(d.normalize(),new L(_[0],_[1]+f,_[2]),.08,16733525,.015,.008))});const p=h.diagnostics.contact_position_w,g=h.diagnostics.actual_contact;p==null||p.forEach((_,m)=>{if(!(g!=null&&g[m])||!_.every(Number.isFinite))return;const d=new me(new li(.012,8,6),new je({color:11184810}));d.position.set(_[0],_[1]+f,_[2]),this.annotations.add(d)})});const e=this.reference.links[this.link],n=this.current.links[this.link],s=[],r=[];e==null||e.traverse(h=>{h.isMesh&&s.push(h)}),n==null||n.traverse(h=>{h.isMesh&&r.push(h)});const a=new L;let o=0;s.forEach((h,u)=>{const f=h.geometry.getAttribute("position"),p=r[u];if(!(!f||!p))for(let g=0;g<f.count;g+=Math.max(1,Math.ceil(f.count/12))){const _=new L().fromBufferAttribute(f,g).applyMatrix4(h.matrixWorld);_.y+=2*this.spacing;const d=new L().fromBufferAttribute(f,g).applyMatrix4(p.matrixWorld).sub(_);a.add(d),o++;const w=d.length();this.displacement&&w>1e-8&&this.annotations.add(new ji(d.normalize(),_,w*this.scale,4255632,Math.min(.025,w*this.scale/4),.01))}}),o&&a.multiplyScalar(100/o);const c=h=>{const u=h.diagnostics,f=p=>typeof p=="number"?p.toFixed(3):"未知";return`${h.label}
全身负距离: ${f(u.full_depth_cm)} cm；双足: ${f(u.feet_depth_cm)} cm
验收（报告）: ${u.static_recovery_pass??"未知"}；保留（报告）: ${u.all_required_kept??"未知"}`};this.details.textContent=`${c(t)}

${c(this.selected)}

灰点：报告中的历史接触标记
${this.link} 材料点平均 dx (cm): ${o?a.toArray().map(h=>h.toFixed(3)).join(", "):"无网格采样"}
箭头显示倍率: ${this.scale}×`}bounds(t){this.reference&&t.expandByObject(this.group)}terrainVisible(t){this.group.children.forEach(e=>{e!==this.reference&&(e.visible=t)})}}class Xx{constructor(t,e,n){se(this,"group",new Fe);se(this,"phases",[]);se(this,"selected",0);se(this,"marker",null);se(this,"details",null);se(this,"rawGroup",new Fe);se(this,"showRaw",!0);this.scene=t,this.jump=e,this.focus=n,t.add(this.group)}clear(){zn(this.group),this.rawGroup.clear(),this.marker=null}setup(t){this.clear(),this.phases=(t==null?void 0:t.kind)==="support_motion"?t.phases??[]:[],this.selected=0;const e=document.getElementById("reviewPanel");if(!this.phases.length)return;e.hidden=!1;const n=document.createElement("p");n.textContent=t.notice,e.append(n);const s=document.createElement("label");s.className="stack-field";const r=document.createElement("span");r.textContent="持续接触阶段";const a=document.createElement("select");a.setAttribute("aria-label","持续接触阶段"),this.phases.forEach((l,h)=>a.add(new Option(`${l.start}–${l.end} ${l.part}`,String(h)))),a.onchange=()=>{this.selected=Number(a.value),this.draw(),this.jump(this.phases[this.selected].start),this.focusSelected()},s.append(r,a),e.append(s);const o=document.createElement("label");o.className="toggle";const c=document.createElement("input");c.type="checkbox",c.checked=this.showRaw,c.onchange=()=>{this.showRaw=c.checked,this.rawGroup.visible=this.showRaw},o.append(c,document.createTextNode("显示原始 rollout 轨迹")),e.append(o),this.details=document.createElement("p"),e.append(this.details),this.draw()}dot(t,e,n){const s=new me(new li(n,10,8),new je({color:e,depthTest:!1}));return s.position.set(...t),s.renderOrder=20,this.group.add(s),s}draw(){this.clear();const t=this.phases[this.selected];if(!t)return;const e=t.part==="left_foot"?15754313:3254232,n=h=>h.map(u=>new L(...u));this.group.add(this.rawGroup),t.rollouts.forEach(h=>{const u=new Bs(new Pe().setFromPoints(n(h)),new Bn({color:e,transparent:!0,opacity:.12,depthTest:!1,depthWrite:!1}));u.renderOrder=15,this.rawGroup.add(u)}),this.rawGroup.visible=this.showRaw;const s=n(t.aggregate),r=new Q0;for(let h=1;h<s.length;h++)s[h].distanceToSquared(s[h-1])>1e-12&&r.add(new Cu(s[h-1],s[h]));const a=new me(new Jc(r,Math.max(8,s.length*2),.0015,6,!1),new je({color:e,depthTest:!1,depthWrite:!1}));a.renderOrder=16,this.group.add(a);const o=s[0],l=s.at(-1).clone().sub(o);if(l.z=0,l.length()>1e-6){const h=new ji(l.clone().normalize(),o,l.length(),e,Math.min(.004,l.length()/6),.0015);h.traverse(u=>{u.material&&(u.material.depthTest=!1)}),h.renderOrder=18,this.group.add(h)}this.marker=this.dot(t.aggregate[0],16777215,.0025),this.details&&(this.details.textContent=`聚合净位移 ${t.aggregate_net_cm.toFixed(2)} cm；原始 rollout 中位数 ${t.rollout_median_net_cm.toFixed(2)} cm。亮色宽线：聚合；淡色细线：原始执行；同一固定材料点。`)}update(t){const e=this.phases[this.selected];!e||!this.marker||(this.marker.visible=t>=e.start&&t<=e.end,this.marker.visible&&this.marker.position.set(...e.aggregate[t-e.start]))}focusSelected(){const t=this.phases[this.selected];t&&this.focus(t.aggregate)}}class qx{constructor(t,e){se(this,"group",new Fe);se(this,"review");se(this,"gain",20);se(this,"frame",0);se(this,"details",null);this.focus=e,t.add(this.group)}clear(){zn(this.group)}setup(t){if(this.clear(),this.review=t,this.details=null,(t==null?void 0:t.kind)!=="support_slip")return;const e=document.getElementById("reviewPanel");e.hidden=!1;const n=document.createElement("p");n.textContent=t.notice,e.append(n);const s=document.createElement("label");s.className="stack-field",s.append(document.createTextNode("位移箭头倍率（不改变统计值）"));const r=document.createElement("input");r.type="number",r.min="1",r.max="100",r.value=String(this.gain),r.onchange=()=>{this.gain=Math.max(1,Math.min(100,Number(r.value)||1)),this.update(this.frame)},s.append(r),e.append(s);const a=document.createElement("button");a.textContent="聚焦当前接触点",a.onclick=()=>{var c,l;const o=((l=(c=this.review)==null?void 0:c.slip_frames)==null?void 0:l[this.frame])??[];o.length&&this.focus(o.map(h=>new L(...h.position)))},e.append(a),this.details=document.createElement("p"),e.append(this.details)}update(t){var h,u,f;if(this.frame=t,this.clear(),((h=this.review)==null?void 0:h.kind)!=="support_slip")return;const e=((u=this.review.slip_frames)==null?void 0:u[t])??[],n=["左脚","右脚","左手","右手","左膝","右膝"],s=p=>`${p.part}:${p.surface}`,r=new Map;e.forEach(p=>r.set(s(p),Math.min(r.get(s(p))??1/0,p.motion_cm))),e.forEach(p=>{const g=p.motion_cm===r.get(s(p))?3594650:15967552,_=new L(...p.position),m=new L(...p.delta),d=new me(new li(.0015,8,6),new je({color:g,depthTest:!1}));d.position.copy(_),d.renderOrder=25,this.group.add(d);const w=m.length()*this.gain;if(w>1e-7){const T=new ji(m.normalize(),_,w,g,Math.min(.004,w*.25),Math.min(.002,w*.12));T.traverse(M=>{M.material&&(M.material.depthTest=!1),M.renderOrder=25}),this.group.add(T)}});const a=[...r].map(([p,g])=>{const[_,m]=p.split(":").map(Number),d=e.filter(M=>s(M)===p).map(M=>M.motion_cm).sort((M,F)=>M-F),w=Math.floor(d.length/2),T=d.length%2?d[w]:(d[w-1]+d[w])/2;return`${n[_]}·面${m}：最低几何运动 ${g.toFixed(3)} / 中位 ${T.toFixed(3)} / 最大 ${d.at(-1).toFixed(3)} cm`}),o=(f=this.review.support_frames)==null?void 0:f[t],c={no_contact:"无有效接触",unloaded:"接触但卸载",load_bearing:"承重",unknown:"未知"},l=o?o.map(p=>{var g,_;return`${n[p.part]} ${c[p.load_state]??"未知"}：${((g=p.normal_force_n)==null?void 0:g.toFixed(1))??"未知"} N，承重点相对切向速度 ${((_=p.loaded_speed_cm_s)==null?void 0:_.toFixed(2))??"未知"} cm/s`}).join("；"):"承重滑移：未知";this.details&&(this.details.textContent=(e.length?`${t}→${t+1}；${a.join("；")}。`:"此帧无可测几何区间，不能记作零滑移。")+l+"。")}}const Wu=document.querySelector("#app");if(!Wu)throw new Error("missing #app root");Hx(Wu);Gx();const Mn=document.querySelector("#scene"),yn=document.querySelector("#timeline"),Ri=new U0({canvas:Mn,antialias:!0,preserveDrawingBuffer:!0});Ri.setPixelRatio(Math.min(window.devicePixelRatio,2));Ri.outputColorSpace=Le;Ri.toneMapping=Kh;Ri.toneMappingExposure=1.08;Ri.shadowMap.enabled=!1;const ze=new Eu;ze.background=new Kt(725014);ze.fog=new jc(725014,9,20);ze.up.set(0,0,1);const Cn=new Je(42,1,.01,100);Cn.up.set(0,0,1);Cn.position.set(3.2,-4.5,2.7);const Tn=new Ev(Cn,Mn);Tn.target.set(0,0,.9);Tn.enableDamping=!0;ze.add(new fv(16055295,1515562,2.4));const Xu=new Uu(16777215,3.1);Xu.position.set(3,-4,7);ze.add(Xu);const qu=new Mv(14,28,3358796,1910576);qu.rotation.x=Math.PI/2;ze.add(qu);let gt=null,sn=null,nn=null;const ju=new qx(ze,i=>{const t=new Xn().setFromPoints(i).getBoundingSphere(new di),e=Cn.position.clone().sub(Tn.target).normalize();Tn.target.copy(t.center),Cn.position.copy(t.center).addScaledVector(e,Math.max(.45,t.radius*5)),Tn.update()});let hr=new Fe;ze.add(hr);const ui=new Qv(Mn,Cn);ze.add(ui.handles,ui.restoreGhosts);let Pi=new Fe;ze.add(Pi);let Ai=new Fe;ze.add(Ai);let kn=null,ke=null,Te=0,ar=!1,Yh=performance.now(),nr=0,Pc="all",Yu="",$u=!0,ur=!1,Ds=!1,Ss=null,Co=!1,Lc=!1,bs=!1,_o=null,Ro=Promise.resolve(),Po=[];function xr(){return Co||Lc||bs||(gt==null?void 0:gt.generation.status)==="running"}async function yr(i){if(xr())return null;Lc=!0,Do.cancel(),Yi();try{return await Ro,await i()}catch(t){return rn(String(t),!0),null}finally{Lc=!1,Yi()}}const dr=new Wx(ze,i=>{gt&&(gt.qpos=[i],Rn(0))}),Nc=new Xx(ze,i=>Rn(i),i=>{const t=i.map(r=>new L(...r)),e=new Xn().setFromPoints(t).getCenter(new L),n=Cn.position.clone().sub(Tn.target).normalize(),s=t.at(-1).clone().sub(t[0]);s.z=0,Tn.target.copy(e),Cn.position.copy(e).addScaledVector(n,s.length()<.05?.48:.95),Tn.update()}),Lo=[1619620,6869905,15754313,16758087,5213439,11958502,3254232,14703261],Ku={LHEE:"left_foot",LTOE:"left_foot",RHEE:"right_foot",RTOE:"right_foot",LH:"left_hand",RH:"right_hand",LK:"left_knee",RK:"right_knee",left_heel:"left_foot",left_toe:"left_foot",right_heel:"right_foot",right_toe:"right_foot",left_hand:"left_hand",right_hand:"right_hand",left_knee:"left_knee",right_knee:"right_knee"};let vo=NaN;try{vo=Number(localStorage.getItem("motion-edit.timeline-height"))}catch{}let Es=Number.isFinite(vo)&&vo>0?vo:window.innerWidth<=760?200:230;function el(i,t=!1){if(Es=Math.max(150,Math.min(window.innerHeight*.48,Math.round(i))),document.documentElement.style.setProperty("--timeline-height",`${Es}px`),t)try{localStorage.setItem("motion-edit.timeline-height",String(Es))}catch{}sl()}el(Es);async function No(){const i=await An("/api/recent-motions"),t=et("recentMotionList");et("recentMotionCount").textContent=String(i.items.length);const e=i.items.map(n=>{const s=document.createElement("button");s.type="button",s.className=`recent-motion-item${n.motion_id===i.active_motion_id?" active":""}`,s.dataset.motionKey=n.motion_id,s.setAttribute("aria-pressed",String(n.motion_id===i.active_motion_id));const r=document.createElement("span");r.className="recent-motion-marker";const a=document.createElement("span");a.className="recent-motion-copy";const o=document.createElement("strong");o.textContent=n.label;const c=document.createElement("small");return c.textContent=n.provenance,a.append(o,c),s.append(r,a),s.onclick=()=>{Wo(n.motion_id)},s});return t.replaceChildren(...e),i.items}function jx(i){document.querySelectorAll(".recent-motion-item").forEach(t=>{const e=t.dataset.motionKey===i;t.classList.toggle("active",e),t.setAttribute("aria-pressed",String(e))})}async function Wo(i,t=!1){if(!(xr()||(gt==null?void 0:gt.motion_id)===i)){Co=!0,jo(!1),Do.cancel(),Yi(),document.querySelectorAll(".recent-motion-item").forEach(e=>e.disabled=!0);try{rn(t?"Opening generated motion":"Opening motion",!1,!0),await Ro;const e=await An("/api/session/load",{method:"POST",body:JSON.stringify({motion_id:i})});Te=0,await Mr(e,!0),await No(),mr(),t&&rn("Generated candidate opened · native validation required")}catch(e){rn(String(e),!0)}finally{Co=!1,Yi()}}}async function Ju(){var t,e;rn("Loading motions",!1,!0),et("retryLoad").hidden=!0,Po=(await An("/api/motions")).motions;let i=null;try{i=await An("/api/session")}catch(n){if(!(n instanceof zu)||n.status!==404)throw n}if(i)await Mr(i,!0),await No(),mr();else{const s=((t=(await No())[0])==null?void 0:t.motion_id)||((e=Po.find(r=>r.ready))==null?void 0:e.motion_id);s?await Wo(s):rn("No motion available. Open a registered motion or a playback file.",!1,!0)}}function Zu(){const i=et("motionSearch").value.trim().toLowerCase(),t=Po.filter(n=>`${n.motion_id} ${n.label} ${n.provenance}`.toLowerCase().includes(i)),e=et("motionPickerList");e.replaceChildren();for(const n of t){const s=document.createElement("button");s.className="motion-picker-item",s.disabled=!n.ready;const r=document.createElement("strong");r.textContent=n.label;const a=document.createElement("small");a.textContent=`${n.motion_id} · ${n.provenance} · ${n.ready?"可打开":"文件缺失"}`,s.append(r,a),s.onclick=()=>{et("motionPicker").close(),Wo(n.motion_id)},e.append(s)}t.length||(e.textContent="没有匹配的轨迹")}et("openMotionBtn").onclick=async()=>{if(!xr())try{Po=(await An("/api/motions")).motions,et("motionSearch").value="",Zu(),et("motionPicker").showModal(),et("motionSearch").focus()}catch(i){rn(String(i),!0)}};et("closeMotionPicker").onclick=()=>et("motionPicker").close();et("motionSearch").oninput=Zu;et("retryLoad").onclick=()=>{Ju().catch(Qu)};function Qu(i){rn(String(i),!0),et("retryLoad").hidden=!1}async function Mr(i,t=!1){var r,a;const e=ke==null?void 0:ke.handle_id,n=gt;gt=i,ke=e&&i.edit_handles.find(o=>o.handle_id===e)||null,Te=Math.min(Te,i.qpos.length-1),t&&((r=i.review)==null?void 0:r.kind)==="support_motion"&&((a=i.review.phases)!=null&&a.length)&&(Te=i.review.phases[0].start),document.body.classList.toggle("review-mode",!!i.review),document.body.classList.toggle("playback-only",i.read_only),et("playbackNotice").hidden=!i.read_only,jx(i.motion_id);const s=i.motion_id;if(et("motionLabel").textContent=s,et("viewportMotion").textContent=s,(t||!n)&&(et("fpsInput").value=String(i.fps)),et("anchorCount").textContent=i.read_only?"Playback only":`${i.edit_handles.length} handles`,et("editCount").textContent=i.read_only?i.review?"Contact unknown":"No contact layer":`${i.pending_edit_count} edits`,et("undoBtn").disabled=!i.can_undo,et("redoBtn").disabled=!i.can_redo,et("planPath").value=i.settings.edit_plan_path||"",et("outputMotion").value=i.settings.output_motion_path||"",et("outputLayer").value=i.settings.output_contact_layer||"",et("outputMotionId").value=i.settings.output_motion_id||"",et("registerMotion").checked=i.settings.register_motion,et("overwriteOutput").checked=i.settings.overwrite,et("sourceLayer").textContent=i.settings.source_contact_layer||"None",et("planStatus").textContent=i.read_only?"Read-only kinematic reference":i.plan?`${i.plan.status} · ${i.plan.edit_count} edits`:"No plan saved",il(i.generation),ty(),pr(),t)try{await Yx(i)}catch(o){throw n?await Mr(n):gt=null,o}else fi(),ke&&Xo(ke);Rn(Te)}async function Yx(i){var t;rn("Loading scene",!1,!0),bs=!0,Yi();try{const e=new Nu,n=new Promise((c,l)=>{e.onLoad=()=>c(),e.onError=h=>l(new Error(`failed to load robot asset: ${h}`))}),s=new Yv(e);s.loadMeshCb=(c,l,h)=>{if(c.toLowerCase().endsWith(".obj")){new kh(l).load(c,u=>h(u),void 0,u=>h(new Fe,u));return}h(new Fe,new Error(`unsupported URDF mesh: ${c}`))};const r=await s.loadAsync(i.robot_urdf_url);await n;let a=null;try{i.terrain_obj_url&&(a=await new kh().loadAsync(i.terrain_obj_url))}catch(c){throw er(r),c}dr.setup(void 0,null,null,[]),sn&&(ze.remove(sn),er(sn)),nn&&(ze.remove(nn),er(nn)),zn(hr),ui.clear(),zn(Pi),zn(Ai),ke=null,kn&&(ze.remove(kn),er(kn),kn=null),sn=r,nn=a;let o=0;if(sn.traverse(c=>{c.isMesh&&o++}),Mn.dataset.robotMeshes=String(o),ze.add(sn),nn){const c=new tv({color:5858672,roughness:.86,metalness:.03}),l=new Set;nn.traverse(h=>{h.isMesh&&((Array.isArray(h.material)?h.material:[h.material]).forEach(u=>l.add(u)),h.material=c)}),l.forEach(h=>h.dispose()),ze.add(nn)}bs=!1,dr.setup(i.review,sn,nn,i.joint_names),Nc.setup(i.review),ju.setup(i.review),id(),Kx(),$x(),Jx(),fi(),rd(),((t=i.review)==null?void 0:t.kind)==="support_motion"&&Nc.focusSelected(),nl(),mr()}finally{bs=!1,Yi()}}function $x(){if(!gt)return;const i=gt.qpos.map(t=>new L(t[0],t[1],t[2]));kn=new Bs(new Pe().setFromPoints(i),new Bn({color:11450306,transparent:!0,opacity:.45})),kn.visible=et("rootPathToggle").checked,ze.add(kn)}function Kx(){if(gt)for(const i of gt.surfaces){if(i.surface_id==="terrain_ground_z0")continue;const t=new L(...i.normal).normalize().multiplyScalar(.002),e=i.metadata.polygon_world;let n;if(e!=null&&e.length&&e.length>=3)n=e.map(o=>new L(o[0],o[1],o[2]).add(t));else{const o=new L(...i.origin),c=new L(...i.tangent_u),l=new L(...i.tangent_v),[h,u]=i.bounds.u,[f,p]=i.bounds.v;n=[o.clone().addScaledVector(c,h).addScaledVector(l,f),o.clone().addScaledVector(c,u).addScaledVector(l,f),o.clone().addScaledVector(c,u).addScaledVector(l,p),o.clone().addScaledVector(c,h).addScaledVector(l,p)].map(g=>g.add(t))}const s=[];for(let o=1;o<n.length-1;o++)s.push(0,o,o+1);const r=new Pe().setFromPoints(n);r.setIndex(s),r.computeVertexNormals();const a=new me(r,new je({color:5087165,transparent:!0,opacity:.08,side:un,depthWrite:!1}));a.userData.surface=i,hr.add(a)}}function td(i){return String(i.metadata.surface_editor_status||"bound")}function ed(i){return Te>=i.start_frame&&Te<i.end_frame}function Dc(i,t){const e=et("positionOffset");if(!i){e.classList.add("disabled"),e.classList.remove("edited"),et("offsetU").textContent="—",et("offsetV").textContent="—";return}const{u:n,v:s}=ex(i,t);e.classList.remove("disabled"),e.classList.toggle("edited",Math.max(Math.abs(n),Math.abs(s))>tx),et("offsetU").textContent=qh(n),et("offsetV").textContent=qh(s)}function nd(){if(!gt)return[];const i=Yu.trim().toLowerCase();return gt.edit_handles.filter(t=>{const e=td(t);if($u&&!ed(t)||Pc!=="all"&&e!==Pc)return!1;const n=Array.isArray(t.metadata.source_bodies)?t.metadata.source_bodies.join(" "):"",s=Array.isArray(t.metadata.patch_roles)?t.metadata.patch_roles.join(" "):"";return!i||`${t.handle_id} ${t.body} ${t.surface_id} ${t.object_id||""} ${n} ${s}`.toLowerCase().includes(i)})}function fi(){if(!gt)return;const i=new Set(nd().map(t=>t.handle_id));ui.rebuild({handles:gt.edit_handles,visibleHandleIds:i,selectedHandle:ke,radius:Number(et("handleSize").value)/1e3}),ui.setVisible(et("handleToggle").checked)}function Jx(){if(!gt)return;zn(Pi),Mn.dataset.contactSample="point-force";const i=gt.contact_force.part_order.length;Mn.dataset.contactPartSlots=String(i);for(let t=0;t<i;t++){const e=new Fe,n=new je({color:Lo[t%Lo.length],depthTest:!0,transparent:!0}),s=new me(new li(.014,14,10),n),r=new me(new zs(.006,.006,1,8),n),a=new me(new Kc(.022,.055,10),n);e.add(s,r,a),e.userData.point=s,e.userData.shaft=r,e.userData.head=a,e.userData.material=n,Pi.add(e)}fr()}function fr(){if(!gt)return;const i=gt;Pi.visible=et("contactSampleToggle").checked;const t=i.contact_force.positions[Te]||[],e=i.contact_force.forces[Te]||[],n=i.contact_force.masks[Te]||[],s=i.contact_force.position_valid[Te]||[];let r=0;Pi.children.forEach((a,o)=>{const c=a,l=o<t.length&&o<e.length&&!!n[o]&&!!s[o];if(c.visible=l,!l)return;r++;const h=new L(...e[o]),u=h.length(),f=Number(et("forceScale").value)/100,p=Math.min(.9,u/1200*f),g=Math.min(.055,p*.35),_=Math.max(.001,p-g);c.position.set(...t[o]),u>1e-5&&c.quaternion.setFromUnitVectors(new L(0,1,0),h.normalize());const m=Ku[i.contact_force.part_order[o]]||i.contact_force.part_order[o],d=!ke||ke.body===m;c.scale.setScalar(ke&&d?1.35:1);const w=c.userData.material;w.opacity=d?1:.22;const T=c.userData.shaft,M=c.userData.head;T.scale.set(1,_,1),T.position.set(0,_/2,0),M.scale.set(1,g/.055,1),M.position.set(0,_+g/2,0),T.visible=u>1e-5,M.visible=u>1e-5}),Mn.dataset.visibleContactParts=String(r),Mn.dataset.selectedContactBody=(ke==null?void 0:ke.body)||""}function id(){if(!gt||!sn||bs)return;const i=gt.qpos[Te];i&&(sn.position.set(i[0],i[1],i[2]),sn.quaternion.set(i[4],i[5],i[6],i[3]),gt.joint_names.forEach((t,e)=>{var n;return(n=sn.setJointValue)==null?void 0:n.call(sn,t,i[7+e])}),dr.update(),Nc.update(Te),ju.update(Te))}function Rn(i){gt!=null&&gt.qpos.length&&(Number.isFinite(i)||(i=Te),Te=Math.max(0,Math.min(gt.qpos.length-1,Math.round(i))),et("frameInput").max=String(gt.qpos.length-1),et("frameInput").value=String(Te),et("frameTotal").textContent=`/ ${gt.qpos.length-1}`,et("viewportFrame").textContent=`Frame ${Te}`,et("viewportTime").textContent=`${(Te/gt.fps).toFixed(2)} s`,id(),fr(),fi(),pr())}function Zx(){return Vu(yn,(gt==null?void 0:gt.contact_force.part_order.length)??8)}function Qx(i,t){return ix(i,t,(gt==null?void 0:gt.qpos.length)??1)}function pr(){rx({canvas:yn,session:gt,frame:Te,selectedHandle:ke,stableCuts:sd(),partColors:Lo})}function sd(){if(!gt)return[];const i=new Set;return gt.graph.transitions.forEach(t=>{var n;i.add(t.start_frame),i.add(Math.max(t.start_frame,t.end_frame-1));const e=(n=t.metadata)==null?void 0:n.stable_anchor_frames;Array.isArray(e)&&e.forEach(s=>i.add(Number(s)))}),[...i].filter(t=>Number.isFinite(t)).sort((t,e)=>t-e)}function ty(){gt&&(et("partLegend").innerHTML=gt.contact_force.part_order.map((i,t)=>`<span><b style="background:#${Lo[t].toString(16).padStart(6,"0")}"></b>${i}</span>`).join(""))}function Xo(i){ke=i;const t=et("selection");if(!i){t.className="selection empty",t.textContent="None",Dc(null),zn(Ai),fr(),pr(),Ic();return}t.className="selection",t.innerHTML=`<strong>${i.body}</strong><code>${i.handle_id}</code><dl><dt>Frames</dt><dd>${i.start_frame}–${i.end_frame}</dd><dt>Surface</dt><dd>${i.surface_id}</dd><dt>Members</dt><dd>${String(i.metadata.member_count||i.member_anchor_ids.length)}</dd><dt>Status</dt><dd>${td(i)}</dd></dl>`,Dc(i),ey(i),fr(),fi(),pr(),Ic()}function ey(i){zn(Ai),Ai.visible=et("guideToggle").checked;const t=new L(...i.world_position),e=[[i.surface_tangent_u,15754313],[i.surface_tangent_v,6869905],[i.surface_normal,5213439]];for(const[n,s]of e){const r=new L(...n).normalize().multiplyScalar(.14),a=new Bs(new Pe().setFromPoints([t.clone().addScaledVector(r,-1),t.clone().add(r)]),new Bn({color:s}));Ai.add(a)}}const Do=new Kv({canvas:Mn,controls:Tn,layer:ui,getSession:()=>gt,isBusy:xr,getSelectedHandle:()=>ke,selectHandle:Xo,updatePositionOffset:Dc,rebuildHandles:fi,restoreHandle:async i=>!!await Is("/api/session/restore-handle",{handle_id:i.handle_id,mode:et("modeSelect").value}),moveHandle:async(i,t)=>!!await Is("/api/session/move-handle",{handle_id:i.handle_id,requested_world_position:t.toArray(),mode:et("modeSelect").value})});function rd(){const i=new Xn;if(sn&&i.expandByObject(sn),nn&&i.expandByObject(nn),dr.bounds(i),i.isEmpty())return;const t=i.getBoundingSphere(new di);Tn.target.copy(t.center),Cn.position.copy(t.center).add(new L(t.radius*1.8,-t.radius*2.4,t.radius*1.35)),Tn.update()}function mr(){_o!==null&&window.clearTimeout(_o),_o=null,et("sceneStatus").classList.add("hidden")}function rn(i,t=!1,e=!1){mr();const n=et("sceneStatus");n.textContent=i,n.classList.remove("hidden"),n.classList.toggle("error",t),n.setAttribute("role",t?"alert":"status"),!t&&!e&&(_o=window.setTimeout(mr,3e3))}function nl(){const i=et("terrainToggle").checked;nn&&(nn.visible=i),dr.terrainVisible(i),hr.visible=et("surfaceToggle").checked,Pi.visible=et("contactSampleToggle").checked,ui.setVisible(et("handleToggle").checked),Ai.visible=et("guideToggle").checked,kn&&(kn.visible=et("rootPathToggle").checked),Mn.dataset.terrainVisible=String((nn==null?void 0:nn.visible)??!1),Mn.dataset.surfacesVisible=String(hr.visible)}function ny(){return{edit_plan_path:et("planPath").value,output_motion_path:et("outputMotion").value,output_contact_layer:et("outputLayer").value,output_motion_id:et("outputMotionId").value,register_motion:et("registerMotion").checked,overwrite:et("overwriteOutput").checked}}function qo(){const i=JSON.stringify(ny()),t=Ro.then(()=>An("/api/session/settings",{method:"PUT",body:i}));return Ro=t.catch(()=>{}),t.then(e=>(gt=e,e))}function od(){Ss!==null&&window.clearTimeout(Ss),Ss=null}function ad(){Ss===null&&(Ss=window.setTimeout(async()=>{try{const i=await An("/api/session/generation");il(i),Ss=null,i.status==="running"?ad():i.status==="succeeded"&&(et("planStatus").textContent="generated",i.output_motion_id?await Wo(i.output_motion_id,!0):await No())}catch(i){od(),rn(String(i),!0),et("retryLoad").hidden=!1}},900))}function Yi(){const i=!!xr(),t=!!(gt!=null&&gt.read_only),e=!!gt&&!t;document.querySelectorAll('[data-page="contact"] .anchor-browser input,[data-page="contact"] .anchor-browser select,[data-page="contact"] .anchor-browser button,[data-page="output"] input,[data-page="output"] button').forEach(n=>n.disabled=i||!e),document.querySelectorAll(".recent-motion-item,#openMotionBtn,#reviewOpen").forEach(n=>n.disabled=i),et("undoBtn").disabled=i||!e||!(gt!=null&&gt.can_undo),et("redoBtn").disabled=i||!e||!(gt!=null&&gt.can_redo),et("saveBtn").disabled=i||!e,et("outputMotionId").disabled=i||!e||!et("registerMotion").checked,document.querySelectorAll("#playBtn,#prevBtn,#nextBtn,#prevCut,#nextCut,#frameInput,#fpsInput").forEach(n=>n.disabled=Co||bs||!gt),et("scene").setAttribute("aria-busy",String(i))}function il(i){gt&&(gt.generation=i);const t=i.status==="running",e=!!(gt!=null&&gt.read_only),n=et("generateBtn"),s=et("generationStatus");if(n.disabled=t||!gt||e,n.innerHTML=t?'<i data-lucide="loader-circle" class="spin"></i><span>Generating</span>':'<i data-lucide="wand-sparkles"></i><span>Generate</span>',tl(),s.className=`generation-status ${i.status}`,i.status==="running"){const r={queued:"Queued",reading_plan:"Reading edit plan",validating:"Validating",loading_motion:"Loading motion",contact_laplacian:"Optimizing contact trajectory",writing_intermediates:"Preparing full-body IK",fullbody_ik:"Solving full-body IK",merging_ik:"Merging IK result",writing_output:"Writing motion",registering:"Registering motion",saving_plan:"Saving edit plan"},a=i.started_at===null?"":` · ${Math.max(0,Math.round(Date.now()/1e3-i.started_at))}s`;s.innerHTML="<strong>Generating reference</strong><span></span>",s.querySelector("span").textContent=`${r[i.stage||""]||"Working"}${a}`}else i.status==="succeeded"?(et("overwriteOutput").checked=!0,s.innerHTML=`<strong>Generated${i.warnings.length?` · ${i.warnings.length} warnings`:""}</strong><span></span>`,s.querySelector("span").textContent=i.output_motion_path||"Output written",s.setAttribute("title",i.output_motion_path||"")):i.status==="failed"?(s.innerHTML="<strong>Generation failed</strong><span></span>",s.querySelector("span").textContent=i.error||"Unknown error",s.setAttribute("title",i.error||"")):e?s.innerHTML="<strong>Playback only</strong><span>Kinematic reference · no contact layer</span>":s.innerHTML="<strong>Ready</strong><span>Contact-aware candidate · native validation required</span>";Yi(),t?ad():od()}function jo(i){ar=i,ar||(nr=0),et("playBtn").innerHTML=`<i data-lucide="${ar?"pause":"play"}"></i>`,tl()}et("playBtn").onclick=()=>jo(!ar);et("prevBtn").onclick=()=>Rn(Te-1);et("nextBtn").onclick=()=>Rn(Te+1);et("frameInput").onchange=i=>Rn(Number(i.target.value));async function Is(i,t){return yr(async()=>{const e=await An(i,{method:"POST",body:t===void 0?void 0:JSON.stringify(t)});return await Mr(e),rn("Session updated"),e})}et("undoBtn").onclick=()=>{Is("/api/session/undo")};et("redoBtn").onclick=()=>{Is("/api/session/redo")};et("saveBtn").onclick=()=>{yr(async()=>{await qo();const i=await An("/api/session/save",{method:"POST"});gt&&(gt.plan=i.plan),i.plan&&(et("planStatus").textContent=`${i.plan.status} · ${i.plan.edit_count} edits`),rn(`Saved ${i.output_contact_layer}`)})};et("focusBtn").onclick=rd;et("terrainToggle").onchange=nl;et("surfaceToggle").onchange=nl;et("handleToggle").onchange=i=>ui.setVisible(i.target.checked);et("contactSampleToggle").onchange=i=>Pi.visible=i.target.checked;et("handleSize").oninput=()=>fi();et("forceScale").oninput=()=>fr();et("rootPathToggle").onchange=i=>{kn&&(kn.visible=i.target.checked)};et("guideToggle").onchange=i=>Ai.visible=i.target.checked;et("anchorSearch").oninput=i=>{Yu=i.target.value,fi()};et("statusFilter").onchange=i=>{Pc=i.target.value,fi()};et("currentOnly").onchange=i=>{$u=i.target.checked,fi()};function Io(i){const t=nd();if(!t.length)return;const e=Math.max(0,t.findIndex(s=>s.handle_id===(ke==null?void 0:ke.handle_id))),n=t[(e+i+t.length)%t.length];Xo(n),Rn(n.start_frame)}et("prevAnchor").onclick=()=>Io(-1);et("nextAnchor").onclick=()=>Io(1);function cd(i){const t=sd();if(!t.length)return;const e=i>0?t:t.slice().reverse(),n=e.find(s=>i>0?s>Te:s<Te)??e[0];Rn(n)}et("prevCut").onclick=()=>cd(-1);et("nextCut").onclick=()=>cd(1);function ld(i,t=!1,e=!1){if(!gt)return;const n=yn.getBoundingClientRect(),s=Zx(),r=i.clientX-n.left,a=i.clientY-n.top,o=Qx(r,s);t&&r>=s.labelW&&Rn(o);const c=Math.floor((a-s.rulerH)/s.rowH);if(e&&c>=0&&c<gt.contact_force.part_order.length){const u=Ku[gt.contact_force.part_order[c]],f=gt.edit_handles.filter(p=>p.body===u&&ed(p));f.length&&Xo(f[0])}const l=et("timelineHover"),h=c>=0&&c<gt.contact_force.part_order.length?gt.contact_force.part_order[c]:"Timeline";l.textContent=`${h} · ${Hu(o/gt.fps)} · frame ${o}`,l.style.left=`${Math.max(s.labelW+44,Math.min(n.width-72,r))}px`,l.classList.remove("hidden")}yn.addEventListener("pointerdown",i=>{gt&&(jo(!1),Ds=!0,yn.setPointerCapture(i.pointerId),yn.classList.add("scrubbing"),ld(i,!0,!0))});yn.addEventListener("pointermove",i=>ld(i,Ds,!1));yn.addEventListener("pointerup",i=>{Ds&&(Ds=!1,yn.releasePointerCapture(i.pointerId),yn.classList.remove("scrubbing"))});yn.addEventListener("pointercancel",()=>{Ds=!1,yn.classList.remove("scrubbing")});yn.addEventListener("pointerleave",()=>{Ds||et("timelineHover").classList.add("hidden")});document.querySelectorAll("#planPath,#outputMotion,#outputLayer,#outputMotionId,#registerMotion,#overwriteOutput").forEach(i=>{i.dataset.generationSetting="",i.addEventListener("change",()=>{et("outputMotionId").disabled=!et("registerMotion").checked,qo().catch(t=>rn(String(t),!0))})});et("validateBtn").onclick=()=>{yr(async()=>{await qo();const i=await An("/api/session/validate",{method:"POST"});et("planStatus").textContent=`${i.plan.status}${i.warnings.length?` · ${i.warnings.length} warnings`:""}`,rn("ContactEditPlan validated")})};et("generateBtn").onclick=()=>{yr(async()=>{await qo();const i=await An("/api/session/generate",{method:"POST",body:JSON.stringify({})});il(i)})};et("reloadBtn").onclick=()=>{Is("/api/session/reload")};et("discardBtn").onclick=()=>{Is("/api/session/discard")};window.addEventListener("keydown",i=>{if(i.code==="Escape"&&Do.active){i.preventDefault(),Do.cancel();return}et("motionPicker").open||i.target.matches("input,select,textarea")||(i.code==="Space"?(i.preventDefault(),et("playBtn").click()):i.code==="ArrowLeft"?Rn(Te-(i.shiftKey?10:1)):i.code==="ArrowRight"?Rn(Te+(i.shiftKey?10:1)):i.code==="BracketLeft"?Io(-1):i.code==="BracketRight"&&Io(1))});let hd=0,ud=0;et("timelineResizer").addEventListener("pointerdown",i=>{ur=!0,hd=i.clientY,ud=Es,et("timelineResizer").setPointerCapture(i.pointerId),document.body.classList.add("resizing-timeline")});et("timelineResizer").addEventListener("pointermove",i=>{ur&&el(ud+hd-i.clientY)});et("timelineResizer").addEventListener("pointerup",i=>{ur&&(ur=!1,et("timelineResizer").releasePointerCapture(i.pointerId),document.body.classList.remove("resizing-timeline"),el(Es,!0))});function sl(){const i=Mn.getBoundingClientRect();i.width<=0||i.height<=0||(Ri.setSize(i.width,i.height,!1),Cn.aspect=i.width/i.height,Cn.updateProjectionMatrix(),pr())}window.addEventListener("resize",sl);sl();function Ic(){ui.updateProjection(ke)}function dd(i){requestAnimationFrame(dd);const t=Math.min(.1,Math.max(0,(i-Yh)/1e3));if(Yh=i,ar&&gt&&(nr+=t*fd(!1),nr>=1)){const e=Math.floor(nr);nr-=e,Rn((Te+e)%gt.qpos.length)}Tn.update(),Ic(),Ri.render(ze,Cn),Mn.dataset.geometryCount=String(Ri.info.memory.geometries)}requestAnimationFrame(dd);function fd(i=!0){const t=et("fpsInput"),e=Number(t.value),n=Number.isFinite(e)&&e>=1?Math.min(240,e):Math.min(240,Math.max(1,(gt==null?void 0:gt.fps)||50));return i&&(t.value=String(n)),n}et("fpsInput").onchange=()=>{fd()};et("timelineResizer").addEventListener("pointercancel",()=>{ur=!1,document.body.classList.remove("resizing-timeline")});et("reviewOpen").onclick=()=>{yr(async()=>{jo(!1),Te=0,rn("Loading playback",!1,!0);const i=await An("/api/review/load",{method:"POST",body:JSON.stringify({path:et("reviewPath").value,terrain:et("reviewTerrain").value||null})});await Mr(i,!0)})};Ju().catch(Qu);
