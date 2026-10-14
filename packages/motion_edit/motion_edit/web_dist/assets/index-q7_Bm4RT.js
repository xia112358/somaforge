var Md=Object.defineProperty;var bd=(i,t,e)=>t in i?Md(i,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):i[t]=e;var qt=(i,t,e)=>bd(i,typeof t!="symbol"?t+"":t,e);(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))n(s);new MutationObserver(s=>{for(const r of s)if(r.type==="childList")for(const a of r.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&n(a)}).observe(document,{childList:!0,subtree:!0});function e(s){const r={};return s.integrity&&(r.integrity=s.integrity),s.referrerPolicy&&(r.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?r.credentials="include":s.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function n(s){if(s.ep)return;s.ep=!0;const r=e(s);fetch(s.href,r)}})();/**
 * @license
 * Copyright 2010-2024 Three.js Authors
 * SPDX-License-Identifier: MIT
 */const Bc="170",bs={ROTATE:0,DOLLY:1,PAN:2},ys={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},Sd=0,pl=1,Ed=2,nu=1,wd=2,oi=3,di=0,fn=1,dn=2,Pi=0,Ss=1,ml=2,gl=3,_l=4,Td=5,qi=100,Ad=101,Cd=102,Rd=103,Pd=104,Ld=200,Nd=201,Dd=202,Id=203,Yo=204,$o=205,Ud=206,Fd=207,Od=208,kd=209,Bd=210,zd=211,Vd=212,Hd=213,Gd=214,Ko=0,Jo=1,Zo=2,Rs=3,Qo=4,tc=5,ec=6,nc=7,ka=0,Wd=1,Xd=2,Li=0,qd=1,jd=2,Yd=3,iu=4,$d=5,Kd=6,Jd=7,vl="attached",Zd="detached",su=300,Ps=301,Ls=302,ic=303,sc=304,Ba=306,Yi=1e3,Bn=1001,rc=1002,Mn=1003,Qd=1004,Dr=1005,xn=1006,no=1007,li=1008,fi=1009,ru=1010,au=1011,pr=1012,zc=1013,Ki=1014,qn=1015,br=1016,Vc=1017,Hc=1018,Ns=1020,ou=35902,cu=1021,lu=1022,Pn=1023,hu=1024,uu=1025,Es=1026,Ds=1027,du=1028,Gc=1029,fu=1030,Wc=1031,Xc=1033,pa=33776,ma=33777,ga=33778,_a=33779,ac=35840,oc=35841,cc=35842,lc=35843,hc=36196,uc=37492,dc=37496,fc=37808,pc=37809,mc=37810,gc=37811,_c=37812,vc=37813,xc=37814,yc=37815,Mc=37816,bc=37817,Sc=37818,Ec=37819,wc=37820,Tc=37821,va=36492,Ac=36494,Cc=36495,pu=36283,Rc=36284,Pc=36285,Lc=36286,ba=2300,Nc=2301,io=2302,xl=2400,yl=2401,Ml=2402,tf=2500,ef=3200,nf=3201,za=0,sf=1,Ci="",Ne="srgb",Hs="srgb-linear",Va="linear",we="srgb",rs=7680,bl=519,rf=512,af=513,of=514,mu=515,cf=516,lf=517,hf=518,uf=519,Sl=35044,El="300 es",hi=2e3,Sa=2001;class ts{addEventListener(t,e){this._listeners===void 0&&(this._listeners={});const n=this._listeners;n[t]===void 0&&(n[t]=[]),n[t].indexOf(e)===-1&&n[t].push(e)}hasEventListener(t,e){if(this._listeners===void 0)return!1;const n=this._listeners;return n[t]!==void 0&&n[t].indexOf(e)!==-1}removeEventListener(t,e){if(this._listeners===void 0)return;const s=this._listeners[t];if(s!==void 0){const r=s.indexOf(e);r!==-1&&s.splice(r,1)}}dispatchEvent(t){if(this._listeners===void 0)return;const n=this._listeners[t.type];if(n!==void 0){t.target=this;const s=n.slice(0);for(let r=0,a=s.length;r<a;r++)s[r].call(this,t);t.target=null}}}const Ze=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"];let wl=1234567;const lr=Math.PI/180,Is=180/Math.PI;function Fi(){const i=Math.random()*4294967295|0,t=Math.random()*4294967295|0,e=Math.random()*4294967295|0,n=Math.random()*4294967295|0;return(Ze[i&255]+Ze[i>>8&255]+Ze[i>>16&255]+Ze[i>>24&255]+"-"+Ze[t&255]+Ze[t>>8&255]+"-"+Ze[t>>16&15|64]+Ze[t>>24&255]+"-"+Ze[e&63|128]+Ze[e>>8&255]+"-"+Ze[e>>16&255]+Ze[e>>24&255]+Ze[n&255]+Ze[n>>8&255]+Ze[n>>16&255]+Ze[n>>24&255]).toLowerCase()}function Ye(i,t,e){return Math.max(t,Math.min(e,i))}function qc(i,t){return(i%t+t)%t}function df(i,t,e,n,s){return n+(i-t)*(s-n)/(e-t)}function ff(i,t,e){return i!==t?(e-i)/(t-i):0}function hr(i,t,e){return(1-e)*i+e*t}function pf(i,t,e,n){return hr(i,t,1-Math.exp(-e*n))}function mf(i,t=1){return t-Math.abs(qc(i,t*2)-t)}function gf(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*(3-2*i))}function _f(i,t,e){return i<=t?0:i>=e?1:(i=(i-t)/(e-t),i*i*i*(i*(i*6-15)+10))}function vf(i,t){return i+Math.floor(Math.random()*(t-i+1))}function xf(i,t){return i+Math.random()*(t-i)}function yf(i){return i*(.5-Math.random())}function Mf(i){i!==void 0&&(wl=i);let t=wl+=1831565813;return t=Math.imul(t^t>>>15,t|1),t^=t+Math.imul(t^t>>>7,t|61),((t^t>>>14)>>>0)/4294967296}function bf(i){return i*lr}function Sf(i){return i*Is}function Ef(i){return(i&i-1)===0&&i!==0}function wf(i){return Math.pow(2,Math.ceil(Math.log(i)/Math.LN2))}function Tf(i){return Math.pow(2,Math.floor(Math.log(i)/Math.LN2))}function Af(i,t,e,n,s){const r=Math.cos,a=Math.sin,o=r(e/2),c=a(e/2),l=r((t+n)/2),h=a((t+n)/2),u=r((t-n)/2),d=a((t-n)/2),f=r((n-t)/2),g=a((n-t)/2);switch(s){case"XYX":i.set(o*h,c*u,c*d,o*l);break;case"YZY":i.set(c*d,o*h,c*u,o*l);break;case"ZXZ":i.set(c*u,c*d,o*h,o*l);break;case"XZX":i.set(o*h,c*g,c*f,o*l);break;case"YXY":i.set(c*f,o*h,c*g,o*l);break;case"ZYZ":i.set(c*g,c*f,o*h,o*l);break;default:console.warn("THREE.MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+s)}}function xs(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return i/4294967295;case Uint16Array:return i/65535;case Uint8Array:return i/255;case Int32Array:return Math.max(i/2147483647,-1);case Int16Array:return Math.max(i/32767,-1);case Int8Array:return Math.max(i/127,-1);default:throw new Error("Invalid component type.")}}function sn(i,t){switch(t.constructor){case Float32Array:return i;case Uint32Array:return Math.round(i*4294967295);case Uint16Array:return Math.round(i*65535);case Uint8Array:return Math.round(i*255);case Int32Array:return Math.round(i*2147483647);case Int16Array:return Math.round(i*32767);case Int8Array:return Math.round(i*127);default:throw new Error("Invalid component type.")}}const Ri={DEG2RAD:lr,RAD2DEG:Is,generateUUID:Fi,clamp:Ye,euclideanModulo:qc,mapLinear:df,inverseLerp:ff,lerp:hr,damp:pf,pingpong:mf,smoothstep:gf,smootherstep:_f,randInt:vf,randFloat:xf,randFloatSpread:yf,seededRandom:Mf,degToRad:bf,radToDeg:Sf,isPowerOfTwo:Ef,ceilPowerOfTwo:wf,floorPowerOfTwo:Tf,setQuaternionFromProperEuler:Af,normalize:sn,denormalize:xs};class At{constructor(t=0,e=0){At.prototype.isVector2=!0,this.x=t,this.y=e}get width(){return this.x}set width(t){this.x=t}get height(){return this.y}set height(t){this.y=t}set(t,e){return this.x=t,this.y=e,this}setScalar(t){return this.x=t,this.y=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y)}copy(t){return this.x=t.x,this.y=t.y,this}add(t){return this.x+=t.x,this.y+=t.y,this}addScalar(t){return this.x+=t,this.y+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this}subScalar(t){return this.x-=t,this.y-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this}multiply(t){return this.x*=t.x,this.y*=t.y,this}multiplyScalar(t){return this.x*=t,this.y*=t,this}divide(t){return this.x/=t.x,this.y/=t.y,this}divideScalar(t){return this.multiplyScalar(1/t)}applyMatrix3(t){const e=this.x,n=this.y,s=t.elements;return this.x=s[0]*e+s[3]*n+s[6],this.y=s[1]*e+s[4]*n+s[7],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(t){return this.x*t.x+this.y*t.y}cross(t){return this.x*t.y-this.y*t.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(Ye(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y;return e*e+n*n}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this}equals(t){return t.x===this.x&&t.y===this.y}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this}rotateAround(t,e){const n=Math.cos(e),s=Math.sin(e),r=this.x-t.x,a=this.y-t.y;return this.x=r*n-a*s+t.x,this.y=r*s+a*n+t.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}}class re{constructor(t,e,n,s,r,a,o,c,l){re.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],t!==void 0&&this.set(t,e,n,s,r,a,o,c,l)}set(t,e,n,s,r,a,o,c,l){const h=this.elements;return h[0]=t,h[1]=s,h[2]=o,h[3]=e,h[4]=r,h[5]=c,h[6]=n,h[7]=a,h[8]=l,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],this}extractBasis(t,e,n){return t.setFromMatrix3Column(this,0),e.setFromMatrix3Column(this,1),n.setFromMatrix3Column(this,2),this}setFromMatrix4(t){const e=t.elements;return this.set(e[0],e[4],e[8],e[1],e[5],e[9],e[2],e[6],e[10]),this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,s=e.elements,r=this.elements,a=n[0],o=n[3],c=n[6],l=n[1],h=n[4],u=n[7],d=n[2],f=n[5],g=n[8],_=s[0],m=s[3],p=s[6],P=s[1],w=s[4],y=s[7],N=s[2],C=s[5],L=s[8];return r[0]=a*_+o*P+c*N,r[3]=a*m+o*w+c*C,r[6]=a*p+o*y+c*L,r[1]=l*_+h*P+u*N,r[4]=l*m+h*w+u*C,r[7]=l*p+h*y+u*L,r[2]=d*_+f*P+g*N,r[5]=d*m+f*w+g*C,r[8]=d*p+f*y+g*L,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[3]*=t,e[6]*=t,e[1]*=t,e[4]*=t,e[7]*=t,e[2]*=t,e[5]*=t,e[8]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8];return e*a*h-e*o*l-n*r*h+n*o*c+s*r*l-s*a*c}invert(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8],u=h*a-o*l,d=o*c-h*r,f=l*r-a*c,g=e*u+n*d+s*f;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);const _=1/g;return t[0]=u*_,t[1]=(s*l-h*n)*_,t[2]=(o*n-s*a)*_,t[3]=d*_,t[4]=(h*e-s*c)*_,t[5]=(s*r-o*e)*_,t[6]=f*_,t[7]=(n*c-l*e)*_,t[8]=(a*e-n*r)*_,this}transpose(){let t;const e=this.elements;return t=e[1],e[1]=e[3],e[3]=t,t=e[2],e[2]=e[6],e[6]=t,t=e[5],e[5]=e[7],e[7]=t,this}getNormalMatrix(t){return this.setFromMatrix4(t).invert().transpose()}transposeIntoArray(t){const e=this.elements;return t[0]=e[0],t[1]=e[3],t[2]=e[6],t[3]=e[1],t[4]=e[4],t[5]=e[7],t[6]=e[2],t[7]=e[5],t[8]=e[8],this}setUvTransform(t,e,n,s,r,a,o){const c=Math.cos(r),l=Math.sin(r);return this.set(n*c,n*l,-n*(c*a+l*o)+a+t,-s*l,s*c,-s*(-l*a+c*o)+o+e,0,0,1),this}scale(t,e){return this.premultiply(so.makeScale(t,e)),this}rotate(t){return this.premultiply(so.makeRotation(-t)),this}translate(t,e){return this.premultiply(so.makeTranslation(t,e)),this}makeTranslation(t,e){return t.isVector2?this.set(1,0,t.x,0,1,t.y,0,0,1):this.set(1,0,t,0,1,e,0,0,1),this}makeRotation(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,n,e,0,0,0,1),this}makeScale(t,e){return this.set(t,0,0,0,e,0,0,0,1),this}equals(t){const e=this.elements,n=t.elements;for(let s=0;s<9;s++)if(e[s]!==n[s])return!1;return!0}fromArray(t,e=0){for(let n=0;n<9;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t}clone(){return new this.constructor().fromArray(this.elements)}}const so=new re;function gu(i){for(let t=i.length-1;t>=0;--t)if(i[t]>=65535)return!0;return!1}function mr(i){return document.createElementNS("http://www.w3.org/1999/xhtml",i)}function Cf(){const i=mr("canvas");return i.style.display="block",i}const Tl={};function rr(i){i in Tl||(Tl[i]=!0,console.warn(i))}function Rf(i,t,e){return new Promise(function(n,s){function r(){switch(i.clientWaitSync(t,i.SYNC_FLUSH_COMMANDS_BIT,0)){case i.WAIT_FAILED:s();break;case i.TIMEOUT_EXPIRED:setTimeout(r,e);break;default:n()}}setTimeout(r,e)})}function Pf(i){const t=i.elements;t[2]=.5*t[2]+.5*t[3],t[6]=.5*t[6]+.5*t[7],t[10]=.5*t[10]+.5*t[11],t[14]=.5*t[14]+.5*t[15]}function Lf(i){const t=i.elements;t[11]===-1?(t[10]=-t[10]-1,t[14]=-t[14]):(t[10]=-t[10],t[14]=-t[14]+1)}const le={enabled:!0,workingColorSpace:Hs,spaces:{},convert:function(i,t,e){return this.enabled===!1||t===e||!t||!e||(this.spaces[t].transfer===we&&(i.r=ui(i.r),i.g=ui(i.g),i.b=ui(i.b)),this.spaces[t].primaries!==this.spaces[e].primaries&&(i.applyMatrix3(this.spaces[t].toXYZ),i.applyMatrix3(this.spaces[e].fromXYZ)),this.spaces[e].transfer===we&&(i.r=ws(i.r),i.g=ws(i.g),i.b=ws(i.b))),i},fromWorkingColorSpace:function(i,t){return this.convert(i,this.workingColorSpace,t)},toWorkingColorSpace:function(i,t){return this.convert(i,t,this.workingColorSpace)},getPrimaries:function(i){return this.spaces[i].primaries},getTransfer:function(i){return i===Ci?Va:this.spaces[i].transfer},getLuminanceCoefficients:function(i,t=this.workingColorSpace){return i.fromArray(this.spaces[t].luminanceCoefficients)},define:function(i){Object.assign(this.spaces,i)},_getMatrix:function(i,t,e){return i.copy(this.spaces[t].toXYZ).multiply(this.spaces[e].fromXYZ)},_getDrawingBufferColorSpace:function(i){return this.spaces[i].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(i=this.workingColorSpace){return this.spaces[i].workingColorSpaceConfig.unpackColorSpace}};function ui(i){return i<.04045?i*.0773993808:Math.pow(i*.9478672986+.0521327014,2.4)}function ws(i){return i<.0031308?i*12.92:1.055*Math.pow(i,.41666)-.055}const Al=[.64,.33,.3,.6,.15,.06],Cl=[.2126,.7152,.0722],Rl=[.3127,.329],Pl=new re().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Ll=new re().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);le.define({[Hs]:{primaries:Al,whitePoint:Rl,transfer:Va,toXYZ:Pl,fromXYZ:Ll,luminanceCoefficients:Cl,workingColorSpaceConfig:{unpackColorSpace:Ne},outputColorSpaceConfig:{drawingBufferColorSpace:Ne}},[Ne]:{primaries:Al,whitePoint:Rl,transfer:we,toXYZ:Pl,fromXYZ:Ll,luminanceCoefficients:Cl,outputColorSpaceConfig:{drawingBufferColorSpace:Ne}}});let as;class Nf{static getDataURL(t){if(/^data:/i.test(t.src)||typeof HTMLCanvasElement>"u")return t.src;let e;if(t instanceof HTMLCanvasElement)e=t;else{as===void 0&&(as=mr("canvas")),as.width=t.width,as.height=t.height;const n=as.getContext("2d");t instanceof ImageData?n.putImageData(t,0,0):n.drawImage(t,0,0,t.width,t.height),e=as}return e.width>2048||e.height>2048?(console.warn("THREE.ImageUtils.getDataURL: Image converted to jpg for performance reasons",t),e.toDataURL("image/jpeg",.6)):e.toDataURL("image/png")}static sRGBToLinear(t){if(typeof HTMLImageElement<"u"&&t instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&t instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&t instanceof ImageBitmap){const e=mr("canvas");e.width=t.width,e.height=t.height;const n=e.getContext("2d");n.drawImage(t,0,0,t.width,t.height);const s=n.getImageData(0,0,t.width,t.height),r=s.data;for(let a=0;a<r.length;a++)r[a]=ui(r[a]/255)*255;return n.putImageData(s,0,0),e}else if(t.data){const e=t.data.slice(0);for(let n=0;n<e.length;n++)e instanceof Uint8Array||e instanceof Uint8ClampedArray?e[n]=Math.floor(ui(e[n]/255)*255):e[n]=ui(e[n]);return{data:e,width:t.width,height:t.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),t}}let Df=0;class _u{constructor(t=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Df++}),this.uuid=Fi(),this.data=t,this.dataReady=!0,this.version=0}set needsUpdate(t){t===!0&&this.version++}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.images[this.uuid]!==void 0)return t.images[this.uuid];const n={uuid:this.uuid,url:""},s=this.data;if(s!==null){let r;if(Array.isArray(s)){r=[];for(let a=0,o=s.length;a<o;a++)s[a].isDataTexture?r.push(ro(s[a].image)):r.push(ro(s[a]))}else r=ro(s);n.url=r}return e||(t.images[this.uuid]=n),n}}function ro(i){return typeof HTMLImageElement<"u"&&i instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&i instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&i instanceof ImageBitmap?Nf.getDataURL(i):i.data?{data:Array.from(i.data),width:i.width,height:i.height,type:i.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}let If=0;class Je extends ts{constructor(t=Je.DEFAULT_IMAGE,e=Je.DEFAULT_MAPPING,n=Bn,s=Bn,r=xn,a=li,o=Pn,c=fi,l=Je.DEFAULT_ANISOTROPY,h=Ci){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:If++}),this.uuid=Fi(),this.name="",this.source=new _u(t),this.mipmaps=[],this.mapping=e,this.channel=0,this.wrapS=n,this.wrapT=s,this.magFilter=r,this.minFilter=a,this.anisotropy=l,this.format=o,this.internalFormat=null,this.type=c,this.offset=new At(0,0),this.repeat=new At(1,1),this.center=new At(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new re,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=h,this.userData={},this.version=0,this.onUpdate=null,this.isRenderTargetTexture=!1,this.pmremVersion=0}get image(){return this.source.data}set image(t=null){this.source.data=t}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}clone(){return new this.constructor().copy(this)}copy(t){return this.name=t.name,this.source=t.source,this.mipmaps=t.mipmaps.slice(0),this.mapping=t.mapping,this.channel=t.channel,this.wrapS=t.wrapS,this.wrapT=t.wrapT,this.magFilter=t.magFilter,this.minFilter=t.minFilter,this.anisotropy=t.anisotropy,this.format=t.format,this.internalFormat=t.internalFormat,this.type=t.type,this.offset.copy(t.offset),this.repeat.copy(t.repeat),this.center.copy(t.center),this.rotation=t.rotation,this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrix.copy(t.matrix),this.generateMipmaps=t.generateMipmaps,this.premultiplyAlpha=t.premultiplyAlpha,this.flipY=t.flipY,this.unpackAlignment=t.unpackAlignment,this.colorSpace=t.colorSpace,this.userData=JSON.parse(JSON.stringify(t.userData)),this.needsUpdate=!0,this}toJSON(t){const e=t===void 0||typeof t=="string";if(!e&&t.textures[this.uuid]!==void 0)return t.textures[this.uuid];const n={metadata:{version:4.6,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(t).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(n.userData=this.userData),e||(t.textures[this.uuid]=n),n}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(t){if(this.mapping!==su)return t;if(t.applyMatrix3(this.matrix),t.x<0||t.x>1)switch(this.wrapS){case Yi:t.x=t.x-Math.floor(t.x);break;case Bn:t.x=t.x<0?0:1;break;case rc:Math.abs(Math.floor(t.x)%2)===1?t.x=Math.ceil(t.x)-t.x:t.x=t.x-Math.floor(t.x);break}if(t.y<0||t.y>1)switch(this.wrapT){case Yi:t.y=t.y-Math.floor(t.y);break;case Bn:t.y=t.y<0?0:1;break;case rc:Math.abs(Math.floor(t.y)%2)===1?t.y=Math.ceil(t.y)-t.y:t.y=t.y-Math.floor(t.y);break}return this.flipY&&(t.y=1-t.y),t}set needsUpdate(t){t===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(t){t===!0&&this.pmremVersion++}}Je.DEFAULT_IMAGE=null;Je.DEFAULT_MAPPING=su;Je.DEFAULT_ANISOTROPY=1;class ye{constructor(t=0,e=0,n=0,s=1){ye.prototype.isVector4=!0,this.x=t,this.y=e,this.z=n,this.w=s}get width(){return this.z}set width(t){this.z=t}get height(){return this.w}set height(t){this.w=t}set(t,e,n,s){return this.x=t,this.y=e,this.z=n,this.w=s,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this.w=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setW(t){return this.w=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;case 3:this.w=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this.w=t.w!==void 0?t.w:1,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this.w+=t.w,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this.w+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this.w=t.w+e.w,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this.w+=t.w*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this.w-=t.w,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this.w-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this.w=t.w-e.w,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this.w*=t.w,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this.w*=t,this}applyMatrix4(t){const e=this.x,n=this.y,s=this.z,r=this.w,a=t.elements;return this.x=a[0]*e+a[4]*n+a[8]*s+a[12]*r,this.y=a[1]*e+a[5]*n+a[9]*s+a[13]*r,this.z=a[2]*e+a[6]*n+a[10]*s+a[14]*r,this.w=a[3]*e+a[7]*n+a[11]*s+a[15]*r,this}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this.w/=t.w,this}divideScalar(t){return this.multiplyScalar(1/t)}setAxisAngleFromQuaternion(t){this.w=2*Math.acos(t.w);const e=Math.sqrt(1-t.w*t.w);return e<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=t.x/e,this.y=t.y/e,this.z=t.z/e),this}setAxisAngleFromRotationMatrix(t){let e,n,s,r;const c=t.elements,l=c[0],h=c[4],u=c[8],d=c[1],f=c[5],g=c[9],_=c[2],m=c[6],p=c[10];if(Math.abs(h-d)<.01&&Math.abs(u-_)<.01&&Math.abs(g-m)<.01){if(Math.abs(h+d)<.1&&Math.abs(u+_)<.1&&Math.abs(g+m)<.1&&Math.abs(l+f+p-3)<.1)return this.set(1,0,0,0),this;e=Math.PI;const w=(l+1)/2,y=(f+1)/2,N=(p+1)/2,C=(h+d)/4,L=(u+_)/4,I=(g+m)/4;return w>y&&w>N?w<.01?(n=0,s=.707106781,r=.707106781):(n=Math.sqrt(w),s=C/n,r=L/n):y>N?y<.01?(n=.707106781,s=0,r=.707106781):(s=Math.sqrt(y),n=C/s,r=I/s):N<.01?(n=.707106781,s=.707106781,r=0):(r=Math.sqrt(N),n=L/r,s=I/r),this.set(n,s,r,e),this}let P=Math.sqrt((m-g)*(m-g)+(u-_)*(u-_)+(d-h)*(d-h));return Math.abs(P)<.001&&(P=1),this.x=(m-g)/P,this.y=(u-_)/P,this.z=(d-h)/P,this.w=Math.acos((l+f+p-1)/2),this}setFromMatrixPosition(t){const e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this.w=e[15],this}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this.w=Math.min(this.w,t.w),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this.w=Math.max(this.w,t.w),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this.w=Math.max(t.w,Math.min(e.w,this.w)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this.w=Math.max(t,Math.min(e,this.w)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z+this.w*t.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this.w+=(t.w-this.w)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this.w=t.w+(e.w-t.w)*n,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z&&t.w===this.w}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this.w=t[e+3],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t[e+3]=this.w,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this.w=t.getW(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}}class Uf extends ts{constructor(t=1,e=1,n={}){super(),this.isRenderTarget=!0,this.width=t,this.height=e,this.depth=1,this.scissor=new ye(0,0,t,e),this.scissorTest=!1,this.viewport=new ye(0,0,t,e);const s={width:t,height:e,depth:1};n=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:xn,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1},n);const r=new Je(s,n.mapping,n.wrapS,n.wrapT,n.magFilter,n.minFilter,n.format,n.type,n.anisotropy,n.colorSpace);r.flipY=!1,r.generateMipmaps=n.generateMipmaps,r.internalFormat=n.internalFormat,this.textures=[];const a=n.count;for(let o=0;o<a;o++)this.textures[o]=r.clone(),this.textures[o].isRenderTargetTexture=!0;this.depthBuffer=n.depthBuffer,this.stencilBuffer=n.stencilBuffer,this.resolveDepthBuffer=n.resolveDepthBuffer,this.resolveStencilBuffer=n.resolveStencilBuffer,this.depthTexture=n.depthTexture,this.samples=n.samples}get texture(){return this.textures[0]}set texture(t){this.textures[0]=t}setSize(t,e,n=1){if(this.width!==t||this.height!==e||this.depth!==n){this.width=t,this.height=e,this.depth=n;for(let s=0,r=this.textures.length;s<r;s++)this.textures[s].image.width=t,this.textures[s].image.height=e,this.textures[s].image.depth=n;this.dispose()}this.viewport.set(0,0,t,e),this.scissor.set(0,0,t,e)}clone(){return new this.constructor().copy(this)}copy(t){this.width=t.width,this.height=t.height,this.depth=t.depth,this.scissor.copy(t.scissor),this.scissorTest=t.scissorTest,this.viewport.copy(t.viewport),this.textures.length=0;for(let n=0,s=t.textures.length;n<s;n++)this.textures[n]=t.textures[n].clone(),this.textures[n].isRenderTargetTexture=!0;const e=Object.assign({},t.texture.image);return this.texture.source=new _u(e),this.depthBuffer=t.depthBuffer,this.stencilBuffer=t.stencilBuffer,this.resolveDepthBuffer=t.resolveDepthBuffer,this.resolveStencilBuffer=t.resolveStencilBuffer,t.depthTexture!==null&&(this.depthTexture=t.depthTexture.clone()),this.samples=t.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}}class Ji extends Uf{constructor(t=1,e=1,n={}){super(t,e,n),this.isWebGLRenderTarget=!0}}class vu extends Je{constructor(t=null,e=1,n=1,s=1){super(null),this.isDataArrayTexture=!0,this.image={data:t,width:e,height:n,depth:s},this.magFilter=Mn,this.minFilter=Mn,this.wrapR=Bn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(t){this.layerUpdates.add(t)}clearLayerUpdates(){this.layerUpdates.clear()}}class Ff extends Je{constructor(t=null,e=1,n=1,s=1){super(null),this.isData3DTexture=!0,this.image={data:t,width:e,height:n,depth:s},this.magFilter=Mn,this.minFilter=Mn,this.wrapR=Bn,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}class Vn{constructor(t=0,e=0,n=0,s=1){this.isQuaternion=!0,this._x=t,this._y=e,this._z=n,this._w=s}static slerpFlat(t,e,n,s,r,a,o){let c=n[s+0],l=n[s+1],h=n[s+2],u=n[s+3];const d=r[a+0],f=r[a+1],g=r[a+2],_=r[a+3];if(o===0){t[e+0]=c,t[e+1]=l,t[e+2]=h,t[e+3]=u;return}if(o===1){t[e+0]=d,t[e+1]=f,t[e+2]=g,t[e+3]=_;return}if(u!==_||c!==d||l!==f||h!==g){let m=1-o;const p=c*d+l*f+h*g+u*_,P=p>=0?1:-1,w=1-p*p;if(w>Number.EPSILON){const N=Math.sqrt(w),C=Math.atan2(N,p*P);m=Math.sin(m*C)/N,o=Math.sin(o*C)/N}const y=o*P;if(c=c*m+d*y,l=l*m+f*y,h=h*m+g*y,u=u*m+_*y,m===1-o){const N=1/Math.sqrt(c*c+l*l+h*h+u*u);c*=N,l*=N,h*=N,u*=N}}t[e]=c,t[e+1]=l,t[e+2]=h,t[e+3]=u}static multiplyQuaternionsFlat(t,e,n,s,r,a){const o=n[s],c=n[s+1],l=n[s+2],h=n[s+3],u=r[a],d=r[a+1],f=r[a+2],g=r[a+3];return t[e]=o*g+h*u+c*f-l*d,t[e+1]=c*g+h*d+l*u-o*f,t[e+2]=l*g+h*f+o*d-c*u,t[e+3]=h*g-o*u-c*d-l*f,t}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get w(){return this._w}set w(t){this._w=t,this._onChangeCallback()}set(t,e,n,s){return this._x=t,this._y=e,this._z=n,this._w=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(t){return this._x=t.x,this._y=t.y,this._z=t.z,this._w=t.w,this._onChangeCallback(),this}setFromEuler(t,e=!0){const n=t._x,s=t._y,r=t._z,a=t._order,o=Math.cos,c=Math.sin,l=o(n/2),h=o(s/2),u=o(r/2),d=c(n/2),f=c(s/2),g=c(r/2);switch(a){case"XYZ":this._x=d*h*u+l*f*g,this._y=l*f*u-d*h*g,this._z=l*h*g+d*f*u,this._w=l*h*u-d*f*g;break;case"YXZ":this._x=d*h*u+l*f*g,this._y=l*f*u-d*h*g,this._z=l*h*g-d*f*u,this._w=l*h*u+d*f*g;break;case"ZXY":this._x=d*h*u-l*f*g,this._y=l*f*u+d*h*g,this._z=l*h*g+d*f*u,this._w=l*h*u-d*f*g;break;case"ZYX":this._x=d*h*u-l*f*g,this._y=l*f*u+d*h*g,this._z=l*h*g-d*f*u,this._w=l*h*u+d*f*g;break;case"YZX":this._x=d*h*u+l*f*g,this._y=l*f*u+d*h*g,this._z=l*h*g-d*f*u,this._w=l*h*u-d*f*g;break;case"XZY":this._x=d*h*u-l*f*g,this._y=l*f*u-d*h*g,this._z=l*h*g+d*f*u,this._w=l*h*u+d*f*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+a)}return e===!0&&this._onChangeCallback(),this}setFromAxisAngle(t,e){const n=e/2,s=Math.sin(n);return this._x=t.x*s,this._y=t.y*s,this._z=t.z*s,this._w=Math.cos(n),this._onChangeCallback(),this}setFromRotationMatrix(t){const e=t.elements,n=e[0],s=e[4],r=e[8],a=e[1],o=e[5],c=e[9],l=e[2],h=e[6],u=e[10],d=n+o+u;if(d>0){const f=.5/Math.sqrt(d+1);this._w=.25/f,this._x=(h-c)*f,this._y=(r-l)*f,this._z=(a-s)*f}else if(n>o&&n>u){const f=2*Math.sqrt(1+n-o-u);this._w=(h-c)/f,this._x=.25*f,this._y=(s+a)/f,this._z=(r+l)/f}else if(o>u){const f=2*Math.sqrt(1+o-n-u);this._w=(r-l)/f,this._x=(s+a)/f,this._y=.25*f,this._z=(c+h)/f}else{const f=2*Math.sqrt(1+u-n-o);this._w=(a-s)/f,this._x=(r+l)/f,this._y=(c+h)/f,this._z=.25*f}return this._onChangeCallback(),this}setFromUnitVectors(t,e){let n=t.dot(e)+1;return n<Number.EPSILON?(n=0,Math.abs(t.x)>Math.abs(t.z)?(this._x=-t.y,this._y=t.x,this._z=0,this._w=n):(this._x=0,this._y=-t.z,this._z=t.y,this._w=n)):(this._x=t.y*e.z-t.z*e.y,this._y=t.z*e.x-t.x*e.z,this._z=t.x*e.y-t.y*e.x,this._w=n),this.normalize()}angleTo(t){return 2*Math.acos(Math.abs(Ye(this.dot(t),-1,1)))}rotateTowards(t,e){const n=this.angleTo(t);if(n===0)return this;const s=Math.min(1,e/n);return this.slerp(t,s),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(t){return this._x*t._x+this._y*t._y+this._z*t._z+this._w*t._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let t=this.length();return t===0?(this._x=0,this._y=0,this._z=0,this._w=1):(t=1/t,this._x=this._x*t,this._y=this._y*t,this._z=this._z*t,this._w=this._w*t),this._onChangeCallback(),this}multiply(t){return this.multiplyQuaternions(this,t)}premultiply(t){return this.multiplyQuaternions(t,this)}multiplyQuaternions(t,e){const n=t._x,s=t._y,r=t._z,a=t._w,o=e._x,c=e._y,l=e._z,h=e._w;return this._x=n*h+a*o+s*l-r*c,this._y=s*h+a*c+r*o-n*l,this._z=r*h+a*l+n*c-s*o,this._w=a*h-n*o-s*c-r*l,this._onChangeCallback(),this}slerp(t,e){if(e===0)return this;if(e===1)return this.copy(t);const n=this._x,s=this._y,r=this._z,a=this._w;let o=a*t._w+n*t._x+s*t._y+r*t._z;if(o<0?(this._w=-t._w,this._x=-t._x,this._y=-t._y,this._z=-t._z,o=-o):this.copy(t),o>=1)return this._w=a,this._x=n,this._y=s,this._z=r,this;const c=1-o*o;if(c<=Number.EPSILON){const f=1-e;return this._w=f*a+e*this._w,this._x=f*n+e*this._x,this._y=f*s+e*this._y,this._z=f*r+e*this._z,this.normalize(),this}const l=Math.sqrt(c),h=Math.atan2(l,o),u=Math.sin((1-e)*h)/l,d=Math.sin(e*h)/l;return this._w=a*u+this._w*d,this._x=n*u+this._x*d,this._y=s*u+this._y*d,this._z=r*u+this._z*d,this._onChangeCallback(),this}slerpQuaternions(t,e,n){return this.copy(t).slerp(e,n)}random(){const t=2*Math.PI*Math.random(),e=2*Math.PI*Math.random(),n=Math.random(),s=Math.sqrt(1-n),r=Math.sqrt(n);return this.set(s*Math.sin(t),s*Math.cos(t),r*Math.sin(e),r*Math.cos(e))}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._w===this._w}fromArray(t,e=0){return this._x=t[e],this._y=t[e+1],this._z=t[e+2],this._w=t[e+3],this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._w,t}fromBufferAttribute(t,e){return this._x=t.getX(e),this._y=t.getY(e),this._z=t.getZ(e),this._w=t.getW(e),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}}class D{constructor(t=0,e=0,n=0){D.prototype.isVector3=!0,this.x=t,this.y=e,this.z=n}set(t,e,n){return n===void 0&&(n=this.z),this.x=t,this.y=e,this.z=n,this}setScalar(t){return this.x=t,this.y=t,this.z=t,this}setX(t){return this.x=t,this}setY(t){return this.y=t,this}setZ(t){return this.z=t,this}setComponent(t,e){switch(t){case 0:this.x=e;break;case 1:this.y=e;break;case 2:this.z=e;break;default:throw new Error("index is out of range: "+t)}return this}getComponent(t){switch(t){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+t)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(t){return this.x=t.x,this.y=t.y,this.z=t.z,this}add(t){return this.x+=t.x,this.y+=t.y,this.z+=t.z,this}addScalar(t){return this.x+=t,this.y+=t,this.z+=t,this}addVectors(t,e){return this.x=t.x+e.x,this.y=t.y+e.y,this.z=t.z+e.z,this}addScaledVector(t,e){return this.x+=t.x*e,this.y+=t.y*e,this.z+=t.z*e,this}sub(t){return this.x-=t.x,this.y-=t.y,this.z-=t.z,this}subScalar(t){return this.x-=t,this.y-=t,this.z-=t,this}subVectors(t,e){return this.x=t.x-e.x,this.y=t.y-e.y,this.z=t.z-e.z,this}multiply(t){return this.x*=t.x,this.y*=t.y,this.z*=t.z,this}multiplyScalar(t){return this.x*=t,this.y*=t,this.z*=t,this}multiplyVectors(t,e){return this.x=t.x*e.x,this.y=t.y*e.y,this.z=t.z*e.z,this}applyEuler(t){return this.applyQuaternion(Nl.setFromEuler(t))}applyAxisAngle(t,e){return this.applyQuaternion(Nl.setFromAxisAngle(t,e))}applyMatrix3(t){const e=this.x,n=this.y,s=this.z,r=t.elements;return this.x=r[0]*e+r[3]*n+r[6]*s,this.y=r[1]*e+r[4]*n+r[7]*s,this.z=r[2]*e+r[5]*n+r[8]*s,this}applyNormalMatrix(t){return this.applyMatrix3(t).normalize()}applyMatrix4(t){const e=this.x,n=this.y,s=this.z,r=t.elements,a=1/(r[3]*e+r[7]*n+r[11]*s+r[15]);return this.x=(r[0]*e+r[4]*n+r[8]*s+r[12])*a,this.y=(r[1]*e+r[5]*n+r[9]*s+r[13])*a,this.z=(r[2]*e+r[6]*n+r[10]*s+r[14])*a,this}applyQuaternion(t){const e=this.x,n=this.y,s=this.z,r=t.x,a=t.y,o=t.z,c=t.w,l=2*(a*s-o*n),h=2*(o*e-r*s),u=2*(r*n-a*e);return this.x=e+c*l+a*u-o*h,this.y=n+c*h+o*l-r*u,this.z=s+c*u+r*h-a*l,this}project(t){return this.applyMatrix4(t.matrixWorldInverse).applyMatrix4(t.projectionMatrix)}unproject(t){return this.applyMatrix4(t.projectionMatrixInverse).applyMatrix4(t.matrixWorld)}transformDirection(t){const e=this.x,n=this.y,s=this.z,r=t.elements;return this.x=r[0]*e+r[4]*n+r[8]*s,this.y=r[1]*e+r[5]*n+r[9]*s,this.z=r[2]*e+r[6]*n+r[10]*s,this.normalize()}divide(t){return this.x/=t.x,this.y/=t.y,this.z/=t.z,this}divideScalar(t){return this.multiplyScalar(1/t)}min(t){return this.x=Math.min(this.x,t.x),this.y=Math.min(this.y,t.y),this.z=Math.min(this.z,t.z),this}max(t){return this.x=Math.max(this.x,t.x),this.y=Math.max(this.y,t.y),this.z=Math.max(this.z,t.z),this}clamp(t,e){return this.x=Math.max(t.x,Math.min(e.x,this.x)),this.y=Math.max(t.y,Math.min(e.y,this.y)),this.z=Math.max(t.z,Math.min(e.z,this.z)),this}clampScalar(t,e){return this.x=Math.max(t,Math.min(e,this.x)),this.y=Math.max(t,Math.min(e,this.y)),this.z=Math.max(t,Math.min(e,this.z)),this}clampLength(t,e){const n=this.length();return this.divideScalar(n||1).multiplyScalar(Math.max(t,Math.min(e,n)))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(t){return this.x*t.x+this.y*t.y+this.z*t.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(t){return this.normalize().multiplyScalar(t)}lerp(t,e){return this.x+=(t.x-this.x)*e,this.y+=(t.y-this.y)*e,this.z+=(t.z-this.z)*e,this}lerpVectors(t,e,n){return this.x=t.x+(e.x-t.x)*n,this.y=t.y+(e.y-t.y)*n,this.z=t.z+(e.z-t.z)*n,this}cross(t){return this.crossVectors(this,t)}crossVectors(t,e){const n=t.x,s=t.y,r=t.z,a=e.x,o=e.y,c=e.z;return this.x=s*c-r*o,this.y=r*a-n*c,this.z=n*o-s*a,this}projectOnVector(t){const e=t.lengthSq();if(e===0)return this.set(0,0,0);const n=t.dot(this)/e;return this.copy(t).multiplyScalar(n)}projectOnPlane(t){return ao.copy(this).projectOnVector(t),this.sub(ao)}reflect(t){return this.sub(ao.copy(t).multiplyScalar(2*this.dot(t)))}angleTo(t){const e=Math.sqrt(this.lengthSq()*t.lengthSq());if(e===0)return Math.PI/2;const n=this.dot(t)/e;return Math.acos(Ye(n,-1,1))}distanceTo(t){return Math.sqrt(this.distanceToSquared(t))}distanceToSquared(t){const e=this.x-t.x,n=this.y-t.y,s=this.z-t.z;return e*e+n*n+s*s}manhattanDistanceTo(t){return Math.abs(this.x-t.x)+Math.abs(this.y-t.y)+Math.abs(this.z-t.z)}setFromSpherical(t){return this.setFromSphericalCoords(t.radius,t.phi,t.theta)}setFromSphericalCoords(t,e,n){const s=Math.sin(e)*t;return this.x=s*Math.sin(n),this.y=Math.cos(e)*t,this.z=s*Math.cos(n),this}setFromCylindrical(t){return this.setFromCylindricalCoords(t.radius,t.theta,t.y)}setFromCylindricalCoords(t,e,n){return this.x=t*Math.sin(e),this.y=n,this.z=t*Math.cos(e),this}setFromMatrixPosition(t){const e=t.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this}setFromMatrixScale(t){const e=this.setFromMatrixColumn(t,0).length(),n=this.setFromMatrixColumn(t,1).length(),s=this.setFromMatrixColumn(t,2).length();return this.x=e,this.y=n,this.z=s,this}setFromMatrixColumn(t,e){return this.fromArray(t.elements,e*4)}setFromMatrix3Column(t,e){return this.fromArray(t.elements,e*3)}setFromEuler(t){return this.x=t._x,this.y=t._y,this.z=t._z,this}setFromColor(t){return this.x=t.r,this.y=t.g,this.z=t.b,this}equals(t){return t.x===this.x&&t.y===this.y&&t.z===this.z}fromArray(t,e=0){return this.x=t[e],this.y=t[e+1],this.z=t[e+2],this}toArray(t=[],e=0){return t[e]=this.x,t[e+1]=this.y,t[e+2]=this.z,t}fromBufferAttribute(t,e){return this.x=t.getX(e),this.y=t.getY(e),this.z=t.getZ(e),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){const t=Math.random()*Math.PI*2,e=Math.random()*2-1,n=Math.sqrt(1-e*e);return this.x=n*Math.cos(t),this.y=e,this.z=n*Math.sin(t),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}}const ao=new D,Nl=new Vn;class Gn{constructor(t=new D(1/0,1/0,1/0),e=new D(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=t,this.max=e}set(t,e){return this.min.copy(t),this.max.copy(e),this}setFromArray(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e+=3)this.expandByPoint(Un.fromArray(t,e));return this}setFromBufferAttribute(t){this.makeEmpty();for(let e=0,n=t.count;e<n;e++)this.expandByPoint(Un.fromBufferAttribute(t,e));return this}setFromPoints(t){this.makeEmpty();for(let e=0,n=t.length;e<n;e++)this.expandByPoint(t[e]);return this}setFromCenterAndSize(t,e){const n=Un.copy(e).multiplyScalar(.5);return this.min.copy(t).sub(n),this.max.copy(t).add(n),this}setFromObject(t,e=!1){return this.makeEmpty(),this.expandByObject(t,e)}clone(){return new this.constructor().copy(this)}copy(t){return this.min.copy(t.min),this.max.copy(t.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(t){return this.isEmpty()?t.set(0,0,0):t.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(t){return this.isEmpty()?t.set(0,0,0):t.subVectors(this.max,this.min)}expandByPoint(t){return this.min.min(t),this.max.max(t),this}expandByVector(t){return this.min.sub(t),this.max.add(t),this}expandByScalar(t){return this.min.addScalar(-t),this.max.addScalar(t),this}expandByObject(t,e=!1){t.updateWorldMatrix(!1,!1);const n=t.geometry;if(n!==void 0){const r=n.getAttribute("position");if(e===!0&&r!==void 0&&t.isInstancedMesh!==!0)for(let a=0,o=r.count;a<o;a++)t.isMesh===!0?t.getVertexPosition(a,Un):Un.fromBufferAttribute(r,a),Un.applyMatrix4(t.matrixWorld),this.expandByPoint(Un);else t.boundingBox!==void 0?(t.boundingBox===null&&t.computeBoundingBox(),Ir.copy(t.boundingBox)):(n.boundingBox===null&&n.computeBoundingBox(),Ir.copy(n.boundingBox)),Ir.applyMatrix4(t.matrixWorld),this.union(Ir)}const s=t.children;for(let r=0,a=s.length;r<a;r++)this.expandByObject(s[r],e);return this}containsPoint(t){return t.x>=this.min.x&&t.x<=this.max.x&&t.y>=this.min.y&&t.y<=this.max.y&&t.z>=this.min.z&&t.z<=this.max.z}containsBox(t){return this.min.x<=t.min.x&&t.max.x<=this.max.x&&this.min.y<=t.min.y&&t.max.y<=this.max.y&&this.min.z<=t.min.z&&t.max.z<=this.max.z}getParameter(t,e){return e.set((t.x-this.min.x)/(this.max.x-this.min.x),(t.y-this.min.y)/(this.max.y-this.min.y),(t.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(t){return t.max.x>=this.min.x&&t.min.x<=this.max.x&&t.max.y>=this.min.y&&t.min.y<=this.max.y&&t.max.z>=this.min.z&&t.min.z<=this.max.z}intersectsSphere(t){return this.clampPoint(t.center,Un),Un.distanceToSquared(t.center)<=t.radius*t.radius}intersectsPlane(t){let e,n;return t.normal.x>0?(e=t.normal.x*this.min.x,n=t.normal.x*this.max.x):(e=t.normal.x*this.max.x,n=t.normal.x*this.min.x),t.normal.y>0?(e+=t.normal.y*this.min.y,n+=t.normal.y*this.max.y):(e+=t.normal.y*this.max.y,n+=t.normal.y*this.min.y),t.normal.z>0?(e+=t.normal.z*this.min.z,n+=t.normal.z*this.max.z):(e+=t.normal.z*this.max.z,n+=t.normal.z*this.min.z),e<=-t.constant&&n>=-t.constant}intersectsTriangle(t){if(this.isEmpty())return!1;this.getCenter(Qs),Ur.subVectors(this.max,Qs),os.subVectors(t.a,Qs),cs.subVectors(t.b,Qs),ls.subVectors(t.c,Qs),xi.subVectors(cs,os),yi.subVectors(ls,cs),Bi.subVectors(os,ls);let e=[0,-xi.z,xi.y,0,-yi.z,yi.y,0,-Bi.z,Bi.y,xi.z,0,-xi.x,yi.z,0,-yi.x,Bi.z,0,-Bi.x,-xi.y,xi.x,0,-yi.y,yi.x,0,-Bi.y,Bi.x,0];return!oo(e,os,cs,ls,Ur)||(e=[1,0,0,0,1,0,0,0,1],!oo(e,os,cs,ls,Ur))?!1:(Fr.crossVectors(xi,yi),e=[Fr.x,Fr.y,Fr.z],oo(e,os,cs,ls,Ur))}clampPoint(t,e){return e.copy(t).clamp(this.min,this.max)}distanceToPoint(t){return this.clampPoint(t,Un).distanceTo(t)}getBoundingSphere(t){return this.isEmpty()?t.makeEmpty():(this.getCenter(t.center),t.radius=this.getSize(Un).length()*.5),t}intersect(t){return this.min.max(t.min),this.max.min(t.max),this.isEmpty()&&this.makeEmpty(),this}union(t){return this.min.min(t.min),this.max.max(t.max),this}applyMatrix4(t){return this.isEmpty()?this:(ti[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(t),ti[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(t),ti[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(t),ti[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(t),ti[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(t),ti[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(t),ti[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(t),ti[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(t),this.setFromPoints(ti),this)}translate(t){return this.min.add(t),this.max.add(t),this}equals(t){return t.min.equals(this.min)&&t.max.equals(this.max)}}const ti=[new D,new D,new D,new D,new D,new D,new D,new D],Un=new D,Ir=new Gn,os=new D,cs=new D,ls=new D,xi=new D,yi=new D,Bi=new D,Qs=new D,Ur=new D,Fr=new D,zi=new D;function oo(i,t,e,n,s){for(let r=0,a=i.length-3;r<=a;r+=3){zi.fromArray(i,r);const o=s.x*Math.abs(zi.x)+s.y*Math.abs(zi.y)+s.z*Math.abs(zi.z),c=t.dot(zi),l=e.dot(zi),h=n.dot(zi);if(Math.max(-Math.max(c,l,h),Math.min(c,l,h))>o)return!1}return!0}const Of=new Gn,tr=new D,co=new D;class gi{constructor(t=new D,e=-1){this.isSphere=!0,this.center=t,this.radius=e}set(t,e){return this.center.copy(t),this.radius=e,this}setFromPoints(t,e){const n=this.center;e!==void 0?n.copy(e):Of.setFromPoints(t).getCenter(n);let s=0;for(let r=0,a=t.length;r<a;r++)s=Math.max(s,n.distanceToSquared(t[r]));return this.radius=Math.sqrt(s),this}copy(t){return this.center.copy(t.center),this.radius=t.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(t){return t.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(t){return t.distanceTo(this.center)-this.radius}intersectsSphere(t){const e=this.radius+t.radius;return t.center.distanceToSquared(this.center)<=e*e}intersectsBox(t){return t.intersectsSphere(this)}intersectsPlane(t){return Math.abs(t.distanceToPoint(this.center))<=this.radius}clampPoint(t,e){const n=this.center.distanceToSquared(t);return e.copy(t),n>this.radius*this.radius&&(e.sub(this.center).normalize(),e.multiplyScalar(this.radius).add(this.center)),e}getBoundingBox(t){return this.isEmpty()?(t.makeEmpty(),t):(t.set(this.center,this.center),t.expandByScalar(this.radius),t)}applyMatrix4(t){return this.center.applyMatrix4(t),this.radius=this.radius*t.getMaxScaleOnAxis(),this}translate(t){return this.center.add(t),this}expandByPoint(t){if(this.isEmpty())return this.center.copy(t),this.radius=0,this;tr.subVectors(t,this.center);const e=tr.lengthSq();if(e>this.radius*this.radius){const n=Math.sqrt(e),s=(n-this.radius)*.5;this.center.addScaledVector(tr,s/n),this.radius+=s}return this}union(t){return t.isEmpty()?this:this.isEmpty()?(this.copy(t),this):(this.center.equals(t.center)===!0?this.radius=Math.max(this.radius,t.radius):(co.subVectors(t.center,this.center).setLength(t.radius),this.expandByPoint(tr.copy(t.center).add(co)),this.expandByPoint(tr.copy(t.center).sub(co))),this)}equals(t){return t.center.equals(this.center)&&t.radius===this.radius}clone(){return new this.constructor().copy(this)}}const ei=new D,lo=new D,Or=new D,Mi=new D,ho=new D,kr=new D,uo=new D;class Gs{constructor(t=new D,e=new D(0,0,-1)){this.origin=t,this.direction=e}set(t,e){return this.origin.copy(t),this.direction.copy(e),this}copy(t){return this.origin.copy(t.origin),this.direction.copy(t.direction),this}at(t,e){return e.copy(this.origin).addScaledVector(this.direction,t)}lookAt(t){return this.direction.copy(t).sub(this.origin).normalize(),this}recast(t){return this.origin.copy(this.at(t,ei)),this}closestPointToPoint(t,e){e.subVectors(t,this.origin);const n=e.dot(this.direction);return n<0?e.copy(this.origin):e.copy(this.origin).addScaledVector(this.direction,n)}distanceToPoint(t){return Math.sqrt(this.distanceSqToPoint(t))}distanceSqToPoint(t){const e=ei.subVectors(t,this.origin).dot(this.direction);return e<0?this.origin.distanceToSquared(t):(ei.copy(this.origin).addScaledVector(this.direction,e),ei.distanceToSquared(t))}distanceSqToSegment(t,e,n,s){lo.copy(t).add(e).multiplyScalar(.5),Or.copy(e).sub(t).normalize(),Mi.copy(this.origin).sub(lo);const r=t.distanceTo(e)*.5,a=-this.direction.dot(Or),o=Mi.dot(this.direction),c=-Mi.dot(Or),l=Mi.lengthSq(),h=Math.abs(1-a*a);let u,d,f,g;if(h>0)if(u=a*c-o,d=a*o-c,g=r*h,u>=0)if(d>=-g)if(d<=g){const _=1/h;u*=_,d*=_,f=u*(u+a*d+2*o)+d*(a*u+d+2*c)+l}else d=r,u=Math.max(0,-(a*d+o)),f=-u*u+d*(d+2*c)+l;else d=-r,u=Math.max(0,-(a*d+o)),f=-u*u+d*(d+2*c)+l;else d<=-g?(u=Math.max(0,-(-a*r+o)),d=u>0?-r:Math.min(Math.max(-r,-c),r),f=-u*u+d*(d+2*c)+l):d<=g?(u=0,d=Math.min(Math.max(-r,-c),r),f=d*(d+2*c)+l):(u=Math.max(0,-(a*r+o)),d=u>0?r:Math.min(Math.max(-r,-c),r),f=-u*u+d*(d+2*c)+l);else d=a>0?-r:r,u=Math.max(0,-(a*d+o)),f=-u*u+d*(d+2*c)+l;return n&&n.copy(this.origin).addScaledVector(this.direction,u),s&&s.copy(lo).addScaledVector(Or,d),f}intersectSphere(t,e){ei.subVectors(t.center,this.origin);const n=ei.dot(this.direction),s=ei.dot(ei)-n*n,r=t.radius*t.radius;if(s>r)return null;const a=Math.sqrt(r-s),o=n-a,c=n+a;return c<0?null:o<0?this.at(c,e):this.at(o,e)}intersectsSphere(t){return this.distanceSqToPoint(t.center)<=t.radius*t.radius}distanceToPlane(t){const e=t.normal.dot(this.direction);if(e===0)return t.distanceToPoint(this.origin)===0?0:null;const n=-(this.origin.dot(t.normal)+t.constant)/e;return n>=0?n:null}intersectPlane(t,e){const n=this.distanceToPlane(t);return n===null?null:this.at(n,e)}intersectsPlane(t){const e=t.distanceToPoint(this.origin);return e===0||t.normal.dot(this.direction)*e<0}intersectBox(t,e){let n,s,r,a,o,c;const l=1/this.direction.x,h=1/this.direction.y,u=1/this.direction.z,d=this.origin;return l>=0?(n=(t.min.x-d.x)*l,s=(t.max.x-d.x)*l):(n=(t.max.x-d.x)*l,s=(t.min.x-d.x)*l),h>=0?(r=(t.min.y-d.y)*h,a=(t.max.y-d.y)*h):(r=(t.max.y-d.y)*h,a=(t.min.y-d.y)*h),n>a||r>s||((r>n||isNaN(n))&&(n=r),(a<s||isNaN(s))&&(s=a),u>=0?(o=(t.min.z-d.z)*u,c=(t.max.z-d.z)*u):(o=(t.max.z-d.z)*u,c=(t.min.z-d.z)*u),n>c||o>s)||((o>n||n!==n)&&(n=o),(c<s||s!==s)&&(s=c),s<0)?null:this.at(n>=0?n:s,e)}intersectsBox(t){return this.intersectBox(t,ei)!==null}intersectTriangle(t,e,n,s,r){ho.subVectors(e,t),kr.subVectors(n,t),uo.crossVectors(ho,kr);let a=this.direction.dot(uo),o;if(a>0){if(s)return null;o=1}else if(a<0)o=-1,a=-a;else return null;Mi.subVectors(this.origin,t);const c=o*this.direction.dot(kr.crossVectors(Mi,kr));if(c<0)return null;const l=o*this.direction.dot(ho.cross(Mi));if(l<0||c+l>a)return null;const h=-o*Mi.dot(uo);return h<0?null:this.at(h/a,r)}applyMatrix4(t){return this.origin.applyMatrix4(t),this.direction.transformDirection(t),this}equals(t){return t.origin.equals(this.origin)&&t.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}}class Yt{constructor(t,e,n,s,r,a,o,c,l,h,u,d,f,g,_,m){Yt.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],t!==void 0&&this.set(t,e,n,s,r,a,o,c,l,h,u,d,f,g,_,m)}set(t,e,n,s,r,a,o,c,l,h,u,d,f,g,_,m){const p=this.elements;return p[0]=t,p[4]=e,p[8]=n,p[12]=s,p[1]=r,p[5]=a,p[9]=o,p[13]=c,p[2]=l,p[6]=h,p[10]=u,p[14]=d,p[3]=f,p[7]=g,p[11]=_,p[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new Yt().fromArray(this.elements)}copy(t){const e=this.elements,n=t.elements;return e[0]=n[0],e[1]=n[1],e[2]=n[2],e[3]=n[3],e[4]=n[4],e[5]=n[5],e[6]=n[6],e[7]=n[7],e[8]=n[8],e[9]=n[9],e[10]=n[10],e[11]=n[11],e[12]=n[12],e[13]=n[13],e[14]=n[14],e[15]=n[15],this}copyPosition(t){const e=this.elements,n=t.elements;return e[12]=n[12],e[13]=n[13],e[14]=n[14],this}setFromMatrix3(t){const e=t.elements;return this.set(e[0],e[3],e[6],0,e[1],e[4],e[7],0,e[2],e[5],e[8],0,0,0,0,1),this}extractBasis(t,e,n){return t.setFromMatrixColumn(this,0),e.setFromMatrixColumn(this,1),n.setFromMatrixColumn(this,2),this}makeBasis(t,e,n){return this.set(t.x,e.x,n.x,0,t.y,e.y,n.y,0,t.z,e.z,n.z,0,0,0,0,1),this}extractRotation(t){const e=this.elements,n=t.elements,s=1/hs.setFromMatrixColumn(t,0).length(),r=1/hs.setFromMatrixColumn(t,1).length(),a=1/hs.setFromMatrixColumn(t,2).length();return e[0]=n[0]*s,e[1]=n[1]*s,e[2]=n[2]*s,e[3]=0,e[4]=n[4]*r,e[5]=n[5]*r,e[6]=n[6]*r,e[7]=0,e[8]=n[8]*a,e[9]=n[9]*a,e[10]=n[10]*a,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromEuler(t){const e=this.elements,n=t.x,s=t.y,r=t.z,a=Math.cos(n),o=Math.sin(n),c=Math.cos(s),l=Math.sin(s),h=Math.cos(r),u=Math.sin(r);if(t.order==="XYZ"){const d=a*h,f=a*u,g=o*h,_=o*u;e[0]=c*h,e[4]=-c*u,e[8]=l,e[1]=f+g*l,e[5]=d-_*l,e[9]=-o*c,e[2]=_-d*l,e[6]=g+f*l,e[10]=a*c}else if(t.order==="YXZ"){const d=c*h,f=c*u,g=l*h,_=l*u;e[0]=d+_*o,e[4]=g*o-f,e[8]=a*l,e[1]=a*u,e[5]=a*h,e[9]=-o,e[2]=f*o-g,e[6]=_+d*o,e[10]=a*c}else if(t.order==="ZXY"){const d=c*h,f=c*u,g=l*h,_=l*u;e[0]=d-_*o,e[4]=-a*u,e[8]=g+f*o,e[1]=f+g*o,e[5]=a*h,e[9]=_-d*o,e[2]=-a*l,e[6]=o,e[10]=a*c}else if(t.order==="ZYX"){const d=a*h,f=a*u,g=o*h,_=o*u;e[0]=c*h,e[4]=g*l-f,e[8]=d*l+_,e[1]=c*u,e[5]=_*l+d,e[9]=f*l-g,e[2]=-l,e[6]=o*c,e[10]=a*c}else if(t.order==="YZX"){const d=a*c,f=a*l,g=o*c,_=o*l;e[0]=c*h,e[4]=_-d*u,e[8]=g*u+f,e[1]=u,e[5]=a*h,e[9]=-o*h,e[2]=-l*h,e[6]=f*u+g,e[10]=d-_*u}else if(t.order==="XZY"){const d=a*c,f=a*l,g=o*c,_=o*l;e[0]=c*h,e[4]=-u,e[8]=l*h,e[1]=d*u+_,e[5]=a*h,e[9]=f*u-g,e[2]=g*u-f,e[6]=o*h,e[10]=_*u+d}return e[3]=0,e[7]=0,e[11]=0,e[12]=0,e[13]=0,e[14]=0,e[15]=1,this}makeRotationFromQuaternion(t){return this.compose(kf,t,Bf)}lookAt(t,e,n){const s=this.elements;return _n.subVectors(t,e),_n.lengthSq()===0&&(_n.z=1),_n.normalize(),bi.crossVectors(n,_n),bi.lengthSq()===0&&(Math.abs(n.z)===1?_n.x+=1e-4:_n.z+=1e-4,_n.normalize(),bi.crossVectors(n,_n)),bi.normalize(),Br.crossVectors(_n,bi),s[0]=bi.x,s[4]=Br.x,s[8]=_n.x,s[1]=bi.y,s[5]=Br.y,s[9]=_n.y,s[2]=bi.z,s[6]=Br.z,s[10]=_n.z,this}multiply(t){return this.multiplyMatrices(this,t)}premultiply(t){return this.multiplyMatrices(t,this)}multiplyMatrices(t,e){const n=t.elements,s=e.elements,r=this.elements,a=n[0],o=n[4],c=n[8],l=n[12],h=n[1],u=n[5],d=n[9],f=n[13],g=n[2],_=n[6],m=n[10],p=n[14],P=n[3],w=n[7],y=n[11],N=n[15],C=s[0],L=s[4],I=s[8],M=s[12],b=s[1],F=s[5],k=s[9],H=s[13],Z=s[2],tt=s[6],O=s[10],et=s[14],W=s[3],lt=s[7],pt=s[11],mt=s[15];return r[0]=a*C+o*b+c*Z+l*W,r[4]=a*L+o*F+c*tt+l*lt,r[8]=a*I+o*k+c*O+l*pt,r[12]=a*M+o*H+c*et+l*mt,r[1]=h*C+u*b+d*Z+f*W,r[5]=h*L+u*F+d*tt+f*lt,r[9]=h*I+u*k+d*O+f*pt,r[13]=h*M+u*H+d*et+f*mt,r[2]=g*C+_*b+m*Z+p*W,r[6]=g*L+_*F+m*tt+p*lt,r[10]=g*I+_*k+m*O+p*pt,r[14]=g*M+_*H+m*et+p*mt,r[3]=P*C+w*b+y*Z+N*W,r[7]=P*L+w*F+y*tt+N*lt,r[11]=P*I+w*k+y*O+N*pt,r[15]=P*M+w*H+y*et+N*mt,this}multiplyScalar(t){const e=this.elements;return e[0]*=t,e[4]*=t,e[8]*=t,e[12]*=t,e[1]*=t,e[5]*=t,e[9]*=t,e[13]*=t,e[2]*=t,e[6]*=t,e[10]*=t,e[14]*=t,e[3]*=t,e[7]*=t,e[11]*=t,e[15]*=t,this}determinant(){const t=this.elements,e=t[0],n=t[4],s=t[8],r=t[12],a=t[1],o=t[5],c=t[9],l=t[13],h=t[2],u=t[6],d=t[10],f=t[14],g=t[3],_=t[7],m=t[11],p=t[15];return g*(+r*c*u-s*l*u-r*o*d+n*l*d+s*o*f-n*c*f)+_*(+e*c*f-e*l*d+r*a*d-s*a*f+s*l*h-r*c*h)+m*(+e*l*u-e*o*f-r*a*u+n*a*f+r*o*h-n*l*h)+p*(-s*o*h-e*c*u+e*o*d+s*a*u-n*a*d+n*c*h)}transpose(){const t=this.elements;let e;return e=t[1],t[1]=t[4],t[4]=e,e=t[2],t[2]=t[8],t[8]=e,e=t[6],t[6]=t[9],t[9]=e,e=t[3],t[3]=t[12],t[12]=e,e=t[7],t[7]=t[13],t[13]=e,e=t[11],t[11]=t[14],t[14]=e,this}setPosition(t,e,n){const s=this.elements;return t.isVector3?(s[12]=t.x,s[13]=t.y,s[14]=t.z):(s[12]=t,s[13]=e,s[14]=n),this}invert(){const t=this.elements,e=t[0],n=t[1],s=t[2],r=t[3],a=t[4],o=t[5],c=t[6],l=t[7],h=t[8],u=t[9],d=t[10],f=t[11],g=t[12],_=t[13],m=t[14],p=t[15],P=u*m*l-_*d*l+_*c*f-o*m*f-u*c*p+o*d*p,w=g*d*l-h*m*l-g*c*f+a*m*f+h*c*p-a*d*p,y=h*_*l-g*u*l+g*o*f-a*_*f-h*o*p+a*u*p,N=g*u*c-h*_*c-g*o*d+a*_*d+h*o*m-a*u*m,C=e*P+n*w+s*y+r*N;if(C===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);const L=1/C;return t[0]=P*L,t[1]=(_*d*r-u*m*r-_*s*f+n*m*f+u*s*p-n*d*p)*L,t[2]=(o*m*r-_*c*r+_*s*l-n*m*l-o*s*p+n*c*p)*L,t[3]=(u*c*r-o*d*r-u*s*l+n*d*l+o*s*f-n*c*f)*L,t[4]=w*L,t[5]=(h*m*r-g*d*r+g*s*f-e*m*f-h*s*p+e*d*p)*L,t[6]=(g*c*r-a*m*r-g*s*l+e*m*l+a*s*p-e*c*p)*L,t[7]=(a*d*r-h*c*r+h*s*l-e*d*l-a*s*f+e*c*f)*L,t[8]=y*L,t[9]=(g*u*r-h*_*r-g*n*f+e*_*f+h*n*p-e*u*p)*L,t[10]=(a*_*r-g*o*r+g*n*l-e*_*l-a*n*p+e*o*p)*L,t[11]=(h*o*r-a*u*r-h*n*l+e*u*l+a*n*f-e*o*f)*L,t[12]=N*L,t[13]=(h*_*s-g*u*s+g*n*d-e*_*d-h*n*m+e*u*m)*L,t[14]=(g*o*s-a*_*s-g*n*c+e*_*c+a*n*m-e*o*m)*L,t[15]=(a*u*s-h*o*s+h*n*c-e*u*c-a*n*d+e*o*d)*L,this}scale(t){const e=this.elements,n=t.x,s=t.y,r=t.z;return e[0]*=n,e[4]*=s,e[8]*=r,e[1]*=n,e[5]*=s,e[9]*=r,e[2]*=n,e[6]*=s,e[10]*=r,e[3]*=n,e[7]*=s,e[11]*=r,this}getMaxScaleOnAxis(){const t=this.elements,e=t[0]*t[0]+t[1]*t[1]+t[2]*t[2],n=t[4]*t[4]+t[5]*t[5]+t[6]*t[6],s=t[8]*t[8]+t[9]*t[9]+t[10]*t[10];return Math.sqrt(Math.max(e,n,s))}makeTranslation(t,e,n){return t.isVector3?this.set(1,0,0,t.x,0,1,0,t.y,0,0,1,t.z,0,0,0,1):this.set(1,0,0,t,0,1,0,e,0,0,1,n,0,0,0,1),this}makeRotationX(t){const e=Math.cos(t),n=Math.sin(t);return this.set(1,0,0,0,0,e,-n,0,0,n,e,0,0,0,0,1),this}makeRotationY(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,0,n,0,0,1,0,0,-n,0,e,0,0,0,0,1),this}makeRotationZ(t){const e=Math.cos(t),n=Math.sin(t);return this.set(e,-n,0,0,n,e,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(t,e){const n=Math.cos(e),s=Math.sin(e),r=1-n,a=t.x,o=t.y,c=t.z,l=r*a,h=r*o;return this.set(l*a+n,l*o-s*c,l*c+s*o,0,l*o+s*c,h*o+n,h*c-s*a,0,l*c-s*o,h*c+s*a,r*c*c+n,0,0,0,0,1),this}makeScale(t,e,n){return this.set(t,0,0,0,0,e,0,0,0,0,n,0,0,0,0,1),this}makeShear(t,e,n,s,r,a){return this.set(1,n,r,0,t,1,a,0,e,s,1,0,0,0,0,1),this}compose(t,e,n){const s=this.elements,r=e._x,a=e._y,o=e._z,c=e._w,l=r+r,h=a+a,u=o+o,d=r*l,f=r*h,g=r*u,_=a*h,m=a*u,p=o*u,P=c*l,w=c*h,y=c*u,N=n.x,C=n.y,L=n.z;return s[0]=(1-(_+p))*N,s[1]=(f+y)*N,s[2]=(g-w)*N,s[3]=0,s[4]=(f-y)*C,s[5]=(1-(d+p))*C,s[6]=(m+P)*C,s[7]=0,s[8]=(g+w)*L,s[9]=(m-P)*L,s[10]=(1-(d+_))*L,s[11]=0,s[12]=t.x,s[13]=t.y,s[14]=t.z,s[15]=1,this}decompose(t,e,n){const s=this.elements;let r=hs.set(s[0],s[1],s[2]).length();const a=hs.set(s[4],s[5],s[6]).length(),o=hs.set(s[8],s[9],s[10]).length();this.determinant()<0&&(r=-r),t.x=s[12],t.y=s[13],t.z=s[14],Fn.copy(this);const l=1/r,h=1/a,u=1/o;return Fn.elements[0]*=l,Fn.elements[1]*=l,Fn.elements[2]*=l,Fn.elements[4]*=h,Fn.elements[5]*=h,Fn.elements[6]*=h,Fn.elements[8]*=u,Fn.elements[9]*=u,Fn.elements[10]*=u,e.setFromRotationMatrix(Fn),n.x=r,n.y=a,n.z=o,this}makePerspective(t,e,n,s,r,a,o=hi){const c=this.elements,l=2*r/(e-t),h=2*r/(n-s),u=(e+t)/(e-t),d=(n+s)/(n-s);let f,g;if(o===hi)f=-(a+r)/(a-r),g=-2*a*r/(a-r);else if(o===Sa)f=-a/(a-r),g=-a*r/(a-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+o);return c[0]=l,c[4]=0,c[8]=u,c[12]=0,c[1]=0,c[5]=h,c[9]=d,c[13]=0,c[2]=0,c[6]=0,c[10]=f,c[14]=g,c[3]=0,c[7]=0,c[11]=-1,c[15]=0,this}makeOrthographic(t,e,n,s,r,a,o=hi){const c=this.elements,l=1/(e-t),h=1/(n-s),u=1/(a-r),d=(e+t)*l,f=(n+s)*h;let g,_;if(o===hi)g=(a+r)*u,_=-2*u;else if(o===Sa)g=r*u,_=-1*u;else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+o);return c[0]=2*l,c[4]=0,c[8]=0,c[12]=-d,c[1]=0,c[5]=2*h,c[9]=0,c[13]=-f,c[2]=0,c[6]=0,c[10]=_,c[14]=-g,c[3]=0,c[7]=0,c[11]=0,c[15]=1,this}equals(t){const e=this.elements,n=t.elements;for(let s=0;s<16;s++)if(e[s]!==n[s])return!1;return!0}fromArray(t,e=0){for(let n=0;n<16;n++)this.elements[n]=t[n+e];return this}toArray(t=[],e=0){const n=this.elements;return t[e]=n[0],t[e+1]=n[1],t[e+2]=n[2],t[e+3]=n[3],t[e+4]=n[4],t[e+5]=n[5],t[e+6]=n[6],t[e+7]=n[7],t[e+8]=n[8],t[e+9]=n[9],t[e+10]=n[10],t[e+11]=n[11],t[e+12]=n[12],t[e+13]=n[13],t[e+14]=n[14],t[e+15]=n[15],t}}const hs=new D,Fn=new Yt,kf=new D(0,0,0),Bf=new D(1,1,1),bi=new D,Br=new D,_n=new D,Dl=new Yt,Il=new Vn;class pn{constructor(t=0,e=0,n=0,s=pn.DEFAULT_ORDER){this.isEuler=!0,this._x=t,this._y=e,this._z=n,this._order=s}get x(){return this._x}set x(t){this._x=t,this._onChangeCallback()}get y(){return this._y}set y(t){this._y=t,this._onChangeCallback()}get z(){return this._z}set z(t){this._z=t,this._onChangeCallback()}get order(){return this._order}set order(t){this._order=t,this._onChangeCallback()}set(t,e,n,s=this._order){return this._x=t,this._y=e,this._z=n,this._order=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(t){return this._x=t._x,this._y=t._y,this._z=t._z,this._order=t._order,this._onChangeCallback(),this}setFromRotationMatrix(t,e=this._order,n=!0){const s=t.elements,r=s[0],a=s[4],o=s[8],c=s[1],l=s[5],h=s[9],u=s[2],d=s[6],f=s[10];switch(e){case"XYZ":this._y=Math.asin(Ye(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(-h,f),this._z=Math.atan2(-a,r)):(this._x=Math.atan2(d,l),this._z=0);break;case"YXZ":this._x=Math.asin(-Ye(h,-1,1)),Math.abs(h)<.9999999?(this._y=Math.atan2(o,f),this._z=Math.atan2(c,l)):(this._y=Math.atan2(-u,r),this._z=0);break;case"ZXY":this._x=Math.asin(Ye(d,-1,1)),Math.abs(d)<.9999999?(this._y=Math.atan2(-u,f),this._z=Math.atan2(-a,l)):(this._y=0,this._z=Math.atan2(c,r));break;case"ZYX":this._y=Math.asin(-Ye(u,-1,1)),Math.abs(u)<.9999999?(this._x=Math.atan2(d,f),this._z=Math.atan2(c,r)):(this._x=0,this._z=Math.atan2(-a,l));break;case"YZX":this._z=Math.asin(Ye(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-h,l),this._y=Math.atan2(-u,r)):(this._x=0,this._y=Math.atan2(o,f));break;case"XZY":this._z=Math.asin(-Ye(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(d,l),this._y=Math.atan2(o,r)):(this._x=Math.atan2(-h,f),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+e)}return this._order=e,n===!0&&this._onChangeCallback(),this}setFromQuaternion(t,e,n){return Dl.makeRotationFromQuaternion(t),this.setFromRotationMatrix(Dl,e,n)}setFromVector3(t,e=this._order){return this.set(t.x,t.y,t.z,e)}reorder(t){return Il.setFromEuler(this),this.setFromQuaternion(Il,t)}equals(t){return t._x===this._x&&t._y===this._y&&t._z===this._z&&t._order===this._order}fromArray(t){return this._x=t[0],this._y=t[1],this._z=t[2],t[3]!==void 0&&(this._order=t[3]),this._onChangeCallback(),this}toArray(t=[],e=0){return t[e]=this._x,t[e+1]=this._y,t[e+2]=this._z,t[e+3]=this._order,t}_onChange(t){return this._onChangeCallback=t,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}}pn.DEFAULT_ORDER="XYZ";class jc{constructor(){this.mask=1}set(t){this.mask=(1<<t|0)>>>0}enable(t){this.mask|=1<<t|0}enableAll(){this.mask=-1}toggle(t){this.mask^=1<<t|0}disable(t){this.mask&=~(1<<t|0)}disableAll(){this.mask=0}test(t){return(this.mask&t.mask)!==0}isEnabled(t){return(this.mask&(1<<t|0))!==0}}let zf=0;const Ul=new D,us=new Vn,ni=new Yt,zr=new D,er=new D,Vf=new D,Hf=new Vn,Fl=new D(1,0,0),Ol=new D(0,1,0),kl=new D(0,0,1),Bl={type:"added"},Gf={type:"removed"},ds={type:"childadded",child:null},fo={type:"childremoved",child:null};class De extends ts{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:zf++}),this.uuid=Fi(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=De.DEFAULT_UP.clone();const t=new D,e=new pn,n=new Vn,s=new D(1,1,1);function r(){n.setFromEuler(e,!1)}function a(){e.setFromQuaternion(n,void 0,!1)}e._onChange(r),n._onChange(a),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:t},rotation:{configurable:!0,enumerable:!0,value:e},quaternion:{configurable:!0,enumerable:!0,value:n},scale:{configurable:!0,enumerable:!0,value:s},modelViewMatrix:{value:new Yt},normalMatrix:{value:new re}}),this.matrix=new Yt,this.matrixWorld=new Yt,this.matrixAutoUpdate=De.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=De.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new jc,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(t){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(t),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(t){return this.quaternion.premultiply(t),this}setRotationFromAxisAngle(t,e){this.quaternion.setFromAxisAngle(t,e)}setRotationFromEuler(t){this.quaternion.setFromEuler(t,!0)}setRotationFromMatrix(t){this.quaternion.setFromRotationMatrix(t)}setRotationFromQuaternion(t){this.quaternion.copy(t)}rotateOnAxis(t,e){return us.setFromAxisAngle(t,e),this.quaternion.multiply(us),this}rotateOnWorldAxis(t,e){return us.setFromAxisAngle(t,e),this.quaternion.premultiply(us),this}rotateX(t){return this.rotateOnAxis(Fl,t)}rotateY(t){return this.rotateOnAxis(Ol,t)}rotateZ(t){return this.rotateOnAxis(kl,t)}translateOnAxis(t,e){return Ul.copy(t).applyQuaternion(this.quaternion),this.position.add(Ul.multiplyScalar(e)),this}translateX(t){return this.translateOnAxis(Fl,t)}translateY(t){return this.translateOnAxis(Ol,t)}translateZ(t){return this.translateOnAxis(kl,t)}localToWorld(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(this.matrixWorld)}worldToLocal(t){return this.updateWorldMatrix(!0,!1),t.applyMatrix4(ni.copy(this.matrixWorld).invert())}lookAt(t,e,n){t.isVector3?zr.copy(t):zr.set(t,e,n);const s=this.parent;this.updateWorldMatrix(!0,!1),er.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?ni.lookAt(er,zr,this.up):ni.lookAt(zr,er,this.up),this.quaternion.setFromRotationMatrix(ni),s&&(ni.extractRotation(s.matrixWorld),us.setFromRotationMatrix(ni),this.quaternion.premultiply(us.invert()))}add(t){if(arguments.length>1){for(let e=0;e<arguments.length;e++)this.add(arguments[e]);return this}return t===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",t),this):(t&&t.isObject3D?(t.removeFromParent(),t.parent=this,this.children.push(t),t.dispatchEvent(Bl),ds.child=t,this.dispatchEvent(ds),ds.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",t),this)}remove(t){if(arguments.length>1){for(let n=0;n<arguments.length;n++)this.remove(arguments[n]);return this}const e=this.children.indexOf(t);return e!==-1&&(t.parent=null,this.children.splice(e,1),t.dispatchEvent(Gf),fo.child=t,this.dispatchEvent(fo),fo.child=null),this}removeFromParent(){const t=this.parent;return t!==null&&t.remove(this),this}clear(){return this.remove(...this.children)}attach(t){return this.updateWorldMatrix(!0,!1),ni.copy(this.matrixWorld).invert(),t.parent!==null&&(t.parent.updateWorldMatrix(!0,!1),ni.multiply(t.parent.matrixWorld)),t.applyMatrix4(ni),t.removeFromParent(),t.parent=this,this.children.push(t),t.updateWorldMatrix(!1,!0),t.dispatchEvent(Bl),ds.child=t,this.dispatchEvent(ds),ds.child=null,this}getObjectById(t){return this.getObjectByProperty("id",t)}getObjectByName(t){return this.getObjectByProperty("name",t)}getObjectByProperty(t,e){if(this[t]===e)return this;for(let n=0,s=this.children.length;n<s;n++){const a=this.children[n].getObjectByProperty(t,e);if(a!==void 0)return a}}getObjectsByProperty(t,e,n=[]){this[t]===e&&n.push(this);const s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].getObjectsByProperty(t,e,n);return n}getWorldPosition(t){return this.updateWorldMatrix(!0,!1),t.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(er,t,Vf),t}getWorldScale(t){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(er,Hf,t),t}getWorldDirection(t){this.updateWorldMatrix(!0,!1);const e=this.matrixWorld.elements;return t.set(e[8],e[9],e[10]).normalize()}raycast(){}traverse(t){t(this);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].traverse(t)}traverseVisible(t){if(this.visible===!1)return;t(this);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].traverseVisible(t)}traverseAncestors(t){const e=this.parent;e!==null&&(t(e),e.traverseAncestors(t))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(t){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||t)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,t=!0);const e=this.children;for(let n=0,s=e.length;n<s;n++)e[n].updateMatrixWorld(t)}updateWorldMatrix(t,e){const n=this.parent;if(t===!0&&n!==null&&n.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),e===!0){const s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].updateWorldMatrix(!1,!0)}}toJSON(t){const e=t===void 0||typeof t=="string",n={};e&&(t={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},n.metadata={version:4.6,type:"Object",generator:"Object3D.toJSON"});const s={};s.uuid=this.uuid,s.type=this.type,this.name!==""&&(s.name=this.name),this.castShadow===!0&&(s.castShadow=!0),this.receiveShadow===!0&&(s.receiveShadow=!0),this.visible===!1&&(s.visible=!1),this.frustumCulled===!1&&(s.frustumCulled=!1),this.renderOrder!==0&&(s.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(s.userData=this.userData),s.layers=this.layers.mask,s.matrix=this.matrix.toArray(),s.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(s.matrixAutoUpdate=!1),this.isInstancedMesh&&(s.type="InstancedMesh",s.count=this.count,s.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(s.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(s.type="BatchedMesh",s.perObjectFrustumCulled=this.perObjectFrustumCulled,s.sortObjects=this.sortObjects,s.drawRanges=this._drawRanges,s.reservedRanges=this._reservedRanges,s.visibility=this._visibility,s.active=this._active,s.bounds=this._bounds.map(o=>({boxInitialized:o.boxInitialized,boxMin:o.box.min.toArray(),boxMax:o.box.max.toArray(),sphereInitialized:o.sphereInitialized,sphereRadius:o.sphere.radius,sphereCenter:o.sphere.center.toArray()})),s.maxInstanceCount=this._maxInstanceCount,s.maxVertexCount=this._maxVertexCount,s.maxIndexCount=this._maxIndexCount,s.geometryInitialized=this._geometryInitialized,s.geometryCount=this._geometryCount,s.matricesTexture=this._matricesTexture.toJSON(t),this._colorsTexture!==null&&(s.colorsTexture=this._colorsTexture.toJSON(t)),this.boundingSphere!==null&&(s.boundingSphere={center:s.boundingSphere.center.toArray(),radius:s.boundingSphere.radius}),this.boundingBox!==null&&(s.boundingBox={min:s.boundingBox.min.toArray(),max:s.boundingBox.max.toArray()}));function r(o,c){return o[c.uuid]===void 0&&(o[c.uuid]=c.toJSON(t)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?s.background=this.background.toJSON():this.background.isTexture&&(s.background=this.background.toJSON(t).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(s.environment=this.environment.toJSON(t).uuid);else if(this.isMesh||this.isLine||this.isPoints){s.geometry=r(t.geometries,this.geometry);const o=this.geometry.parameters;if(o!==void 0&&o.shapes!==void 0){const c=o.shapes;if(Array.isArray(c))for(let l=0,h=c.length;l<h;l++){const u=c[l];r(t.shapes,u)}else r(t.shapes,c)}}if(this.isSkinnedMesh&&(s.bindMode=this.bindMode,s.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(t.skeletons,this.skeleton),s.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){const o=[];for(let c=0,l=this.material.length;c<l;c++)o.push(r(t.materials,this.material[c]));s.material=o}else s.material=r(t.materials,this.material);if(this.children.length>0){s.children=[];for(let o=0;o<this.children.length;o++)s.children.push(this.children[o].toJSON(t).object)}if(this.animations.length>0){s.animations=[];for(let o=0;o<this.animations.length;o++){const c=this.animations[o];s.animations.push(r(t.animations,c))}}if(e){const o=a(t.geometries),c=a(t.materials),l=a(t.textures),h=a(t.images),u=a(t.shapes),d=a(t.skeletons),f=a(t.animations),g=a(t.nodes);o.length>0&&(n.geometries=o),c.length>0&&(n.materials=c),l.length>0&&(n.textures=l),h.length>0&&(n.images=h),u.length>0&&(n.shapes=u),d.length>0&&(n.skeletons=d),f.length>0&&(n.animations=f),g.length>0&&(n.nodes=g)}return n.object=s,n;function a(o){const c=[];for(const l in o){const h=o[l];delete h.metadata,c.push(h)}return c}}clone(t){return new this.constructor().copy(this,t)}copy(t,e=!0){if(this.name=t.name,this.up.copy(t.up),this.position.copy(t.position),this.rotation.order=t.rotation.order,this.quaternion.copy(t.quaternion),this.scale.copy(t.scale),this.matrix.copy(t.matrix),this.matrixWorld.copy(t.matrixWorld),this.matrixAutoUpdate=t.matrixAutoUpdate,this.matrixWorldAutoUpdate=t.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=t.matrixWorldNeedsUpdate,this.layers.mask=t.layers.mask,this.visible=t.visible,this.castShadow=t.castShadow,this.receiveShadow=t.receiveShadow,this.frustumCulled=t.frustumCulled,this.renderOrder=t.renderOrder,this.animations=t.animations.slice(),this.userData=JSON.parse(JSON.stringify(t.userData)),e===!0)for(let n=0;n<t.children.length;n++){const s=t.children[n];this.add(s.clone())}return this}}De.DEFAULT_UP=new D(0,1,0);De.DEFAULT_MATRIX_AUTO_UPDATE=!0;De.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;const On=new D,ii=new D,po=new D,si=new D,fs=new D,ps=new D,zl=new D,mo=new D,go=new D,_o=new D,vo=new ye,xo=new ye,yo=new ye;class kn{constructor(t=new D,e=new D,n=new D){this.a=t,this.b=e,this.c=n}static getNormal(t,e,n,s){s.subVectors(n,e),On.subVectors(t,e),s.cross(On);const r=s.lengthSq();return r>0?s.multiplyScalar(1/Math.sqrt(r)):s.set(0,0,0)}static getBarycoord(t,e,n,s,r){On.subVectors(s,e),ii.subVectors(n,e),po.subVectors(t,e);const a=On.dot(On),o=On.dot(ii),c=On.dot(po),l=ii.dot(ii),h=ii.dot(po),u=a*l-o*o;if(u===0)return r.set(0,0,0),null;const d=1/u,f=(l*c-o*h)*d,g=(a*h-o*c)*d;return r.set(1-f-g,g,f)}static containsPoint(t,e,n,s){return this.getBarycoord(t,e,n,s,si)===null?!1:si.x>=0&&si.y>=0&&si.x+si.y<=1}static getInterpolation(t,e,n,s,r,a,o,c){return this.getBarycoord(t,e,n,s,si)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(r,si.x),c.addScaledVector(a,si.y),c.addScaledVector(o,si.z),c)}static getInterpolatedAttribute(t,e,n,s,r,a){return vo.setScalar(0),xo.setScalar(0),yo.setScalar(0),vo.fromBufferAttribute(t,e),xo.fromBufferAttribute(t,n),yo.fromBufferAttribute(t,s),a.setScalar(0),a.addScaledVector(vo,r.x),a.addScaledVector(xo,r.y),a.addScaledVector(yo,r.z),a}static isFrontFacing(t,e,n,s){return On.subVectors(n,e),ii.subVectors(t,e),On.cross(ii).dot(s)<0}set(t,e,n){return this.a.copy(t),this.b.copy(e),this.c.copy(n),this}setFromPointsAndIndices(t,e,n,s){return this.a.copy(t[e]),this.b.copy(t[n]),this.c.copy(t[s]),this}setFromAttributeAndIndices(t,e,n,s){return this.a.fromBufferAttribute(t,e),this.b.fromBufferAttribute(t,n),this.c.fromBufferAttribute(t,s),this}clone(){return new this.constructor().copy(this)}copy(t){return this.a.copy(t.a),this.b.copy(t.b),this.c.copy(t.c),this}getArea(){return On.subVectors(this.c,this.b),ii.subVectors(this.a,this.b),On.cross(ii).length()*.5}getMidpoint(t){return t.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(t){return kn.getNormal(this.a,this.b,this.c,t)}getPlane(t){return t.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(t,e){return kn.getBarycoord(t,this.a,this.b,this.c,e)}getInterpolation(t,e,n,s,r){return kn.getInterpolation(t,this.a,this.b,this.c,e,n,s,r)}containsPoint(t){return kn.containsPoint(t,this.a,this.b,this.c)}isFrontFacing(t){return kn.isFrontFacing(this.a,this.b,this.c,t)}intersectsBox(t){return t.intersectsTriangle(this)}closestPointToPoint(t,e){const n=this.a,s=this.b,r=this.c;let a,o;fs.subVectors(s,n),ps.subVectors(r,n),mo.subVectors(t,n);const c=fs.dot(mo),l=ps.dot(mo);if(c<=0&&l<=0)return e.copy(n);go.subVectors(t,s);const h=fs.dot(go),u=ps.dot(go);if(h>=0&&u<=h)return e.copy(s);const d=c*u-h*l;if(d<=0&&c>=0&&h<=0)return a=c/(c-h),e.copy(n).addScaledVector(fs,a);_o.subVectors(t,r);const f=fs.dot(_o),g=ps.dot(_o);if(g>=0&&f<=g)return e.copy(r);const _=f*l-c*g;if(_<=0&&l>=0&&g<=0)return o=l/(l-g),e.copy(n).addScaledVector(ps,o);const m=h*g-f*u;if(m<=0&&u-h>=0&&f-g>=0)return zl.subVectors(r,s),o=(u-h)/(u-h+(f-g)),e.copy(s).addScaledVector(zl,o);const p=1/(m+_+d);return a=_*p,o=d*p,e.copy(n).addScaledVector(fs,a).addScaledVector(ps,o)}equals(t){return t.a.equals(this.a)&&t.b.equals(this.b)&&t.c.equals(this.c)}}const xu={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},Si={h:0,s:0,l:0},Vr={h:0,s:0,l:0};function Mo(i,t,e){return e<0&&(e+=1),e>1&&(e-=1),e<1/6?i+(t-i)*6*e:e<1/2?t:e<2/3?i+(t-i)*6*(2/3-e):i}class Jt{constructor(t,e,n){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(t,e,n)}set(t,e,n){if(e===void 0&&n===void 0){const s=t;s&&s.isColor?this.copy(s):typeof s=="number"?this.setHex(s):typeof s=="string"&&this.setStyle(s)}else this.setRGB(t,e,n);return this}setScalar(t){return this.r=t,this.g=t,this.b=t,this}setHex(t,e=Ne){return t=Math.floor(t),this.r=(t>>16&255)/255,this.g=(t>>8&255)/255,this.b=(t&255)/255,le.toWorkingColorSpace(this,e),this}setRGB(t,e,n,s=le.workingColorSpace){return this.r=t,this.g=e,this.b=n,le.toWorkingColorSpace(this,s),this}setHSL(t,e,n,s=le.workingColorSpace){if(t=qc(t,1),e=Ye(e,0,1),n=Ye(n,0,1),e===0)this.r=this.g=this.b=n;else{const r=n<=.5?n*(1+e):n+e-n*e,a=2*n-r;this.r=Mo(a,r,t+1/3),this.g=Mo(a,r,t),this.b=Mo(a,r,t-1/3)}return le.toWorkingColorSpace(this,s),this}setStyle(t,e=Ne){function n(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+t+" will be ignored.")}let s;if(s=/^(\w+)\(([^\)]*)\)/.exec(t)){let r;const a=s[1],o=s[2];switch(a){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,e);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,e);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return n(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,e);break;default:console.warn("THREE.Color: Unknown color model "+t)}}else if(s=/^\#([A-Fa-f\d]+)$/.exec(t)){const r=s[1],a=r.length;if(a===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,e);if(a===6)return this.setHex(parseInt(r,16),e);console.warn("THREE.Color: Invalid hex color "+t)}else if(t&&t.length>0)return this.setColorName(t,e);return this}setColorName(t,e=Ne){const n=xu[t.toLowerCase()];return n!==void 0?this.setHex(n,e):console.warn("THREE.Color: Unknown color "+t),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(t){return this.r=t.r,this.g=t.g,this.b=t.b,this}copySRGBToLinear(t){return this.r=ui(t.r),this.g=ui(t.g),this.b=ui(t.b),this}copyLinearToSRGB(t){return this.r=ws(t.r),this.g=ws(t.g),this.b=ws(t.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(t=Ne){return le.fromWorkingColorSpace(Qe.copy(this),t),Math.round(Ye(Qe.r*255,0,255))*65536+Math.round(Ye(Qe.g*255,0,255))*256+Math.round(Ye(Qe.b*255,0,255))}getHexString(t=Ne){return("000000"+this.getHex(t).toString(16)).slice(-6)}getHSL(t,e=le.workingColorSpace){le.fromWorkingColorSpace(Qe.copy(this),e);const n=Qe.r,s=Qe.g,r=Qe.b,a=Math.max(n,s,r),o=Math.min(n,s,r);let c,l;const h=(o+a)/2;if(o===a)c=0,l=0;else{const u=a-o;switch(l=h<=.5?u/(a+o):u/(2-a-o),a){case n:c=(s-r)/u+(s<r?6:0);break;case s:c=(r-n)/u+2;break;case r:c=(n-s)/u+4;break}c/=6}return t.h=c,t.s=l,t.l=h,t}getRGB(t,e=le.workingColorSpace){return le.fromWorkingColorSpace(Qe.copy(this),e),t.r=Qe.r,t.g=Qe.g,t.b=Qe.b,t}getStyle(t=Ne){le.fromWorkingColorSpace(Qe.copy(this),t);const e=Qe.r,n=Qe.g,s=Qe.b;return t!==Ne?`color(${t} ${e.toFixed(3)} ${n.toFixed(3)} ${s.toFixed(3)})`:`rgb(${Math.round(e*255)},${Math.round(n*255)},${Math.round(s*255)})`}offsetHSL(t,e,n){return this.getHSL(Si),this.setHSL(Si.h+t,Si.s+e,Si.l+n)}add(t){return this.r+=t.r,this.g+=t.g,this.b+=t.b,this}addColors(t,e){return this.r=t.r+e.r,this.g=t.g+e.g,this.b=t.b+e.b,this}addScalar(t){return this.r+=t,this.g+=t,this.b+=t,this}sub(t){return this.r=Math.max(0,this.r-t.r),this.g=Math.max(0,this.g-t.g),this.b=Math.max(0,this.b-t.b),this}multiply(t){return this.r*=t.r,this.g*=t.g,this.b*=t.b,this}multiplyScalar(t){return this.r*=t,this.g*=t,this.b*=t,this}lerp(t,e){return this.r+=(t.r-this.r)*e,this.g+=(t.g-this.g)*e,this.b+=(t.b-this.b)*e,this}lerpColors(t,e,n){return this.r=t.r+(e.r-t.r)*n,this.g=t.g+(e.g-t.g)*n,this.b=t.b+(e.b-t.b)*n,this}lerpHSL(t,e){this.getHSL(Si),t.getHSL(Vr);const n=hr(Si.h,Vr.h,e),s=hr(Si.s,Vr.s,e),r=hr(Si.l,Vr.l,e);return this.setHSL(n,s,r),this}setFromVector3(t){return this.r=t.x,this.g=t.y,this.b=t.z,this}applyMatrix3(t){const e=this.r,n=this.g,s=this.b,r=t.elements;return this.r=r[0]*e+r[3]*n+r[6]*s,this.g=r[1]*e+r[4]*n+r[7]*s,this.b=r[2]*e+r[5]*n+r[8]*s,this}equals(t){return t.r===this.r&&t.g===this.g&&t.b===this.b}fromArray(t,e=0){return this.r=t[e],this.g=t[e+1],this.b=t[e+2],this}toArray(t=[],e=0){return t[e]=this.r,t[e+1]=this.g,t[e+2]=this.b,t}fromBufferAttribute(t,e){return this.r=t.getX(e),this.g=t.getY(e),this.b=t.getZ(e),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}}const Qe=new Jt;Jt.NAMES=xu;let Wf=0;class Hn extends ts{static get type(){return"Material"}get type(){return this.constructor.type}set type(t){}constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:Wf++}),this.uuid=Fi(),this.name="",this.blending=Ss,this.side=di,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=Yo,this.blendDst=$o,this.blendEquation=qi,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Jt(0,0,0),this.blendAlpha=0,this.depthFunc=Rs,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=bl,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=rs,this.stencilZFail=rs,this.stencilZPass=rs,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(t){this._alphaTest>0!=t>0&&this.version++,this._alphaTest=t}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(t){if(t!==void 0)for(const e in t){const n=t[e];if(n===void 0){console.warn(`THREE.Material: parameter '${e}' has value of undefined.`);continue}const s=this[e];if(s===void 0){console.warn(`THREE.Material: '${e}' is not a property of THREE.${this.type}.`);continue}s&&s.isColor?s.set(n):s&&s.isVector3&&n&&n.isVector3?s.copy(n):this[e]=n}}toJSON(t){const e=t===void 0||typeof t=="string";e&&(t={textures:{},images:{}});const n={metadata:{version:4.6,type:"Material",generator:"Material.toJSON"}};n.uuid=this.uuid,n.type=this.type,this.name!==""&&(n.name=this.name),this.color&&this.color.isColor&&(n.color=this.color.getHex()),this.roughness!==void 0&&(n.roughness=this.roughness),this.metalness!==void 0&&(n.metalness=this.metalness),this.sheen!==void 0&&(n.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(n.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(n.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(n.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(n.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(n.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(n.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(n.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(n.shininess=this.shininess),this.clearcoat!==void 0&&(n.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(n.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(n.clearcoatMap=this.clearcoatMap.toJSON(t).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(n.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(t).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(n.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(t).uuid,n.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.dispersion!==void 0&&(n.dispersion=this.dispersion),this.iridescence!==void 0&&(n.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(n.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(n.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(n.iridescenceMap=this.iridescenceMap.toJSON(t).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(n.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(t).uuid),this.anisotropy!==void 0&&(n.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(n.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(n.anisotropyMap=this.anisotropyMap.toJSON(t).uuid),this.map&&this.map.isTexture&&(n.map=this.map.toJSON(t).uuid),this.matcap&&this.matcap.isTexture&&(n.matcap=this.matcap.toJSON(t).uuid),this.alphaMap&&this.alphaMap.isTexture&&(n.alphaMap=this.alphaMap.toJSON(t).uuid),this.lightMap&&this.lightMap.isTexture&&(n.lightMap=this.lightMap.toJSON(t).uuid,n.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(n.aoMap=this.aoMap.toJSON(t).uuid,n.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(n.bumpMap=this.bumpMap.toJSON(t).uuid,n.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(n.normalMap=this.normalMap.toJSON(t).uuid,n.normalMapType=this.normalMapType,n.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(n.displacementMap=this.displacementMap.toJSON(t).uuid,n.displacementScale=this.displacementScale,n.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(n.roughnessMap=this.roughnessMap.toJSON(t).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(n.metalnessMap=this.metalnessMap.toJSON(t).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(n.emissiveMap=this.emissiveMap.toJSON(t).uuid),this.specularMap&&this.specularMap.isTexture&&(n.specularMap=this.specularMap.toJSON(t).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(n.specularIntensityMap=this.specularIntensityMap.toJSON(t).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(n.specularColorMap=this.specularColorMap.toJSON(t).uuid),this.envMap&&this.envMap.isTexture&&(n.envMap=this.envMap.toJSON(t).uuid,this.combine!==void 0&&(n.combine=this.combine)),this.envMapRotation!==void 0&&(n.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(n.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(n.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(n.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(n.gradientMap=this.gradientMap.toJSON(t).uuid),this.transmission!==void 0&&(n.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(n.transmissionMap=this.transmissionMap.toJSON(t).uuid),this.thickness!==void 0&&(n.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(n.thicknessMap=this.thicknessMap.toJSON(t).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(n.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(n.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(n.size=this.size),this.shadowSide!==null&&(n.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(n.sizeAttenuation=this.sizeAttenuation),this.blending!==Ss&&(n.blending=this.blending),this.side!==di&&(n.side=this.side),this.vertexColors===!0&&(n.vertexColors=!0),this.opacity<1&&(n.opacity=this.opacity),this.transparent===!0&&(n.transparent=!0),this.blendSrc!==Yo&&(n.blendSrc=this.blendSrc),this.blendDst!==$o&&(n.blendDst=this.blendDst),this.blendEquation!==qi&&(n.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(n.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(n.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(n.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(n.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(n.blendAlpha=this.blendAlpha),this.depthFunc!==Rs&&(n.depthFunc=this.depthFunc),this.depthTest===!1&&(n.depthTest=this.depthTest),this.depthWrite===!1&&(n.depthWrite=this.depthWrite),this.colorWrite===!1&&(n.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(n.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==bl&&(n.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(n.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(n.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==rs&&(n.stencilFail=this.stencilFail),this.stencilZFail!==rs&&(n.stencilZFail=this.stencilZFail),this.stencilZPass!==rs&&(n.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(n.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(n.rotation=this.rotation),this.polygonOffset===!0&&(n.polygonOffset=!0),this.polygonOffsetFactor!==0&&(n.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(n.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(n.linewidth=this.linewidth),this.dashSize!==void 0&&(n.dashSize=this.dashSize),this.gapSize!==void 0&&(n.gapSize=this.gapSize),this.scale!==void 0&&(n.scale=this.scale),this.dithering===!0&&(n.dithering=!0),this.alphaTest>0&&(n.alphaTest=this.alphaTest),this.alphaHash===!0&&(n.alphaHash=!0),this.alphaToCoverage===!0&&(n.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(n.premultipliedAlpha=!0),this.forceSinglePass===!0&&(n.forceSinglePass=!0),this.wireframe===!0&&(n.wireframe=!0),this.wireframeLinewidth>1&&(n.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(n.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(n.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(n.flatShading=!0),this.visible===!1&&(n.visible=!1),this.toneMapped===!1&&(n.toneMapped=!1),this.fog===!1&&(n.fog=!1),Object.keys(this.userData).length>0&&(n.userData=this.userData);function s(r){const a=[];for(const o in r){const c=r[o];delete c.metadata,a.push(c)}return a}if(e){const r=s(t.textures),a=s(t.images);r.length>0&&(n.textures=r),a.length>0&&(n.images=a)}return n}clone(){return new this.constructor().copy(this)}copy(t){this.name=t.name,this.blending=t.blending,this.side=t.side,this.vertexColors=t.vertexColors,this.opacity=t.opacity,this.transparent=t.transparent,this.blendSrc=t.blendSrc,this.blendDst=t.blendDst,this.blendEquation=t.blendEquation,this.blendSrcAlpha=t.blendSrcAlpha,this.blendDstAlpha=t.blendDstAlpha,this.blendEquationAlpha=t.blendEquationAlpha,this.blendColor.copy(t.blendColor),this.blendAlpha=t.blendAlpha,this.depthFunc=t.depthFunc,this.depthTest=t.depthTest,this.depthWrite=t.depthWrite,this.stencilWriteMask=t.stencilWriteMask,this.stencilFunc=t.stencilFunc,this.stencilRef=t.stencilRef,this.stencilFuncMask=t.stencilFuncMask,this.stencilFail=t.stencilFail,this.stencilZFail=t.stencilZFail,this.stencilZPass=t.stencilZPass,this.stencilWrite=t.stencilWrite;const e=t.clippingPlanes;let n=null;if(e!==null){const s=e.length;n=new Array(s);for(let r=0;r!==s;++r)n[r]=e[r].clone()}return this.clippingPlanes=n,this.clipIntersection=t.clipIntersection,this.clipShadows=t.clipShadows,this.shadowSide=t.shadowSide,this.colorWrite=t.colorWrite,this.precision=t.precision,this.polygonOffset=t.polygonOffset,this.polygonOffsetFactor=t.polygonOffsetFactor,this.polygonOffsetUnits=t.polygonOffsetUnits,this.dithering=t.dithering,this.alphaTest=t.alphaTest,this.alphaHash=t.alphaHash,this.alphaToCoverage=t.alphaToCoverage,this.premultipliedAlpha=t.premultipliedAlpha,this.forceSinglePass=t.forceSinglePass,this.visible=t.visible,this.toneMapped=t.toneMapped,this.userData=JSON.parse(JSON.stringify(t.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(t){t===!0&&this.version++}onBuild(){console.warn("Material: onBuild() has been removed.")}}class Ke extends Hn{static get type(){return"MeshBasicMaterial"}constructor(t){super(),this.isMeshBasicMaterial=!0,this.color=new Jt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new pn,this.combine=ka,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.fog=t.fog,this}}const Ve=new D,Hr=new At;class bn{constructor(t,e,n=!1){if(Array.isArray(t))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,this.name="",this.array=t,this.itemSize=e,this.count=t!==void 0?t.length/e:0,this.normalized=n,this.usage=Sl,this.updateRanges=[],this.gpuType=qn,this.version=0}onUploadCallback(){}set needsUpdate(t){t===!0&&this.version++}setUsage(t){return this.usage=t,this}addUpdateRange(t,e){this.updateRanges.push({start:t,count:e})}clearUpdateRanges(){this.updateRanges.length=0}copy(t){return this.name=t.name,this.array=new t.array.constructor(t.array),this.itemSize=t.itemSize,this.count=t.count,this.normalized=t.normalized,this.usage=t.usage,this.gpuType=t.gpuType,this}copyAt(t,e,n){t*=this.itemSize,n*=e.itemSize;for(let s=0,r=this.itemSize;s<r;s++)this.array[t+s]=e.array[n+s];return this}copyArray(t){return this.array.set(t),this}applyMatrix3(t){if(this.itemSize===2)for(let e=0,n=this.count;e<n;e++)Hr.fromBufferAttribute(this,e),Hr.applyMatrix3(t),this.setXY(e,Hr.x,Hr.y);else if(this.itemSize===3)for(let e=0,n=this.count;e<n;e++)Ve.fromBufferAttribute(this,e),Ve.applyMatrix3(t),this.setXYZ(e,Ve.x,Ve.y,Ve.z);return this}applyMatrix4(t){for(let e=0,n=this.count;e<n;e++)Ve.fromBufferAttribute(this,e),Ve.applyMatrix4(t),this.setXYZ(e,Ve.x,Ve.y,Ve.z);return this}applyNormalMatrix(t){for(let e=0,n=this.count;e<n;e++)Ve.fromBufferAttribute(this,e),Ve.applyNormalMatrix(t),this.setXYZ(e,Ve.x,Ve.y,Ve.z);return this}transformDirection(t){for(let e=0,n=this.count;e<n;e++)Ve.fromBufferAttribute(this,e),Ve.transformDirection(t),this.setXYZ(e,Ve.x,Ve.y,Ve.z);return this}set(t,e=0){return this.array.set(t,e),this}getComponent(t,e){let n=this.array[t*this.itemSize+e];return this.normalized&&(n=xs(n,this.array)),n}setComponent(t,e,n){return this.normalized&&(n=sn(n,this.array)),this.array[t*this.itemSize+e]=n,this}getX(t){let e=this.array[t*this.itemSize];return this.normalized&&(e=xs(e,this.array)),e}setX(t,e){return this.normalized&&(e=sn(e,this.array)),this.array[t*this.itemSize]=e,this}getY(t){let e=this.array[t*this.itemSize+1];return this.normalized&&(e=xs(e,this.array)),e}setY(t,e){return this.normalized&&(e=sn(e,this.array)),this.array[t*this.itemSize+1]=e,this}getZ(t){let e=this.array[t*this.itemSize+2];return this.normalized&&(e=xs(e,this.array)),e}setZ(t,e){return this.normalized&&(e=sn(e,this.array)),this.array[t*this.itemSize+2]=e,this}getW(t){let e=this.array[t*this.itemSize+3];return this.normalized&&(e=xs(e,this.array)),e}setW(t,e){return this.normalized&&(e=sn(e,this.array)),this.array[t*this.itemSize+3]=e,this}setXY(t,e,n){return t*=this.itemSize,this.normalized&&(e=sn(e,this.array),n=sn(n,this.array)),this.array[t+0]=e,this.array[t+1]=n,this}setXYZ(t,e,n,s){return t*=this.itemSize,this.normalized&&(e=sn(e,this.array),n=sn(n,this.array),s=sn(s,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=s,this}setXYZW(t,e,n,s,r){return t*=this.itemSize,this.normalized&&(e=sn(e,this.array),n=sn(n,this.array),s=sn(s,this.array),r=sn(r,this.array)),this.array[t+0]=e,this.array[t+1]=n,this.array[t+2]=s,this.array[t+3]=r,this}onUpload(t){return this.onUploadCallback=t,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){const t={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(t.name=this.name),this.usage!==Sl&&(t.usage=this.usage),t}}class yu extends bn{constructor(t,e,n){super(new Uint16Array(t),e,n)}}class Mu extends bn{constructor(t,e,n){super(new Uint32Array(t),e,n)}}class ie extends bn{constructor(t,e,n){super(new Float32Array(t),e,n)}}let Xf=0;const Cn=new Yt,bo=new De,ms=new D,vn=new Gn,nr=new Gn,je=new D;class Le extends ts{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:Xf++}),this.uuid=Fi(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(t){return Array.isArray(t)?this.index=new(gu(t)?Mu:yu)(t,1):this.index=t,this}setIndirect(t){return this.indirect=t,this}getIndirect(){return this.indirect}getAttribute(t){return this.attributes[t]}setAttribute(t,e){return this.attributes[t]=e,this}deleteAttribute(t){return delete this.attributes[t],this}hasAttribute(t){return this.attributes[t]!==void 0}addGroup(t,e,n=0){this.groups.push({start:t,count:e,materialIndex:n})}clearGroups(){this.groups=[]}setDrawRange(t,e){this.drawRange.start=t,this.drawRange.count=e}applyMatrix4(t){const e=this.attributes.position;e!==void 0&&(e.applyMatrix4(t),e.needsUpdate=!0);const n=this.attributes.normal;if(n!==void 0){const r=new re().getNormalMatrix(t);n.applyNormalMatrix(r),n.needsUpdate=!0}const s=this.attributes.tangent;return s!==void 0&&(s.transformDirection(t),s.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(t){return Cn.makeRotationFromQuaternion(t),this.applyMatrix4(Cn),this}rotateX(t){return Cn.makeRotationX(t),this.applyMatrix4(Cn),this}rotateY(t){return Cn.makeRotationY(t),this.applyMatrix4(Cn),this}rotateZ(t){return Cn.makeRotationZ(t),this.applyMatrix4(Cn),this}translate(t,e,n){return Cn.makeTranslation(t,e,n),this.applyMatrix4(Cn),this}scale(t,e,n){return Cn.makeScale(t,e,n),this.applyMatrix4(Cn),this}lookAt(t){return bo.lookAt(t),bo.updateMatrix(),this.applyMatrix4(bo.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(ms).negate(),this.translate(ms.x,ms.y,ms.z),this}setFromPoints(t){const e=this.getAttribute("position");if(e===void 0){const n=[];for(let s=0,r=t.length;s<r;s++){const a=t[s];n.push(a.x,a.y,a.z||0)}this.setAttribute("position",new ie(n,3))}else{for(let n=0,s=e.count;n<s;n++){const r=t[n];e.setXYZ(n,r.x,r.y,r.z||0)}t.length>e.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),e.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Gn);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new D(-1/0,-1/0,-1/0),new D(1/0,1/0,1/0));return}if(t!==void 0){if(this.boundingBox.setFromBufferAttribute(t),e)for(let n=0,s=e.length;n<s;n++){const r=e[n];vn.setFromBufferAttribute(r),this.morphTargetsRelative?(je.addVectors(this.boundingBox.min,vn.min),this.boundingBox.expandByPoint(je),je.addVectors(this.boundingBox.max,vn.max),this.boundingBox.expandByPoint(je)):(this.boundingBox.expandByPoint(vn.min),this.boundingBox.expandByPoint(vn.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new gi);const t=this.attributes.position,e=this.morphAttributes.position;if(t&&t.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new D,1/0);return}if(t){const n=this.boundingSphere.center;if(vn.setFromBufferAttribute(t),e)for(let r=0,a=e.length;r<a;r++){const o=e[r];nr.setFromBufferAttribute(o),this.morphTargetsRelative?(je.addVectors(vn.min,nr.min),vn.expandByPoint(je),je.addVectors(vn.max,nr.max),vn.expandByPoint(je)):(vn.expandByPoint(nr.min),vn.expandByPoint(nr.max))}vn.getCenter(n);let s=0;for(let r=0,a=t.count;r<a;r++)je.fromBufferAttribute(t,r),s=Math.max(s,n.distanceToSquared(je));if(e)for(let r=0,a=e.length;r<a;r++){const o=e[r],c=this.morphTargetsRelative;for(let l=0,h=o.count;l<h;l++)je.fromBufferAttribute(o,l),c&&(ms.fromBufferAttribute(t,l),je.add(ms)),s=Math.max(s,n.distanceToSquared(je))}this.boundingSphere.radius=Math.sqrt(s),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){const t=this.index,e=this.attributes;if(t===null||e.position===void 0||e.normal===void 0||e.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}const n=e.position,s=e.normal,r=e.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new bn(new Float32Array(4*n.count),4));const a=this.getAttribute("tangent"),o=[],c=[];for(let I=0;I<n.count;I++)o[I]=new D,c[I]=new D;const l=new D,h=new D,u=new D,d=new At,f=new At,g=new At,_=new D,m=new D;function p(I,M,b){l.fromBufferAttribute(n,I),h.fromBufferAttribute(n,M),u.fromBufferAttribute(n,b),d.fromBufferAttribute(r,I),f.fromBufferAttribute(r,M),g.fromBufferAttribute(r,b),h.sub(l),u.sub(l),f.sub(d),g.sub(d);const F=1/(f.x*g.y-g.x*f.y);isFinite(F)&&(_.copy(h).multiplyScalar(g.y).addScaledVector(u,-f.y).multiplyScalar(F),m.copy(u).multiplyScalar(f.x).addScaledVector(h,-g.x).multiplyScalar(F),o[I].add(_),o[M].add(_),o[b].add(_),c[I].add(m),c[M].add(m),c[b].add(m))}let P=this.groups;P.length===0&&(P=[{start:0,count:t.count}]);for(let I=0,M=P.length;I<M;++I){const b=P[I],F=b.start,k=b.count;for(let H=F,Z=F+k;H<Z;H+=3)p(t.getX(H+0),t.getX(H+1),t.getX(H+2))}const w=new D,y=new D,N=new D,C=new D;function L(I){N.fromBufferAttribute(s,I),C.copy(N);const M=o[I];w.copy(M),w.sub(N.multiplyScalar(N.dot(M))).normalize(),y.crossVectors(C,M);const F=y.dot(c[I])<0?-1:1;a.setXYZW(I,w.x,w.y,w.z,F)}for(let I=0,M=P.length;I<M;++I){const b=P[I],F=b.start,k=b.count;for(let H=F,Z=F+k;H<Z;H+=3)L(t.getX(H+0)),L(t.getX(H+1)),L(t.getX(H+2))}}computeVertexNormals(){const t=this.index,e=this.getAttribute("position");if(e!==void 0){let n=this.getAttribute("normal");if(n===void 0)n=new bn(new Float32Array(e.count*3),3),this.setAttribute("normal",n);else for(let d=0,f=n.count;d<f;d++)n.setXYZ(d,0,0,0);const s=new D,r=new D,a=new D,o=new D,c=new D,l=new D,h=new D,u=new D;if(t)for(let d=0,f=t.count;d<f;d+=3){const g=t.getX(d+0),_=t.getX(d+1),m=t.getX(d+2);s.fromBufferAttribute(e,g),r.fromBufferAttribute(e,_),a.fromBufferAttribute(e,m),h.subVectors(a,r),u.subVectors(s,r),h.cross(u),o.fromBufferAttribute(n,g),c.fromBufferAttribute(n,_),l.fromBufferAttribute(n,m),o.add(h),c.add(h),l.add(h),n.setXYZ(g,o.x,o.y,o.z),n.setXYZ(_,c.x,c.y,c.z),n.setXYZ(m,l.x,l.y,l.z)}else for(let d=0,f=e.count;d<f;d+=3)s.fromBufferAttribute(e,d+0),r.fromBufferAttribute(e,d+1),a.fromBufferAttribute(e,d+2),h.subVectors(a,r),u.subVectors(s,r),h.cross(u),n.setXYZ(d+0,h.x,h.y,h.z),n.setXYZ(d+1,h.x,h.y,h.z),n.setXYZ(d+2,h.x,h.y,h.z);this.normalizeNormals(),n.needsUpdate=!0}}normalizeNormals(){const t=this.attributes.normal;for(let e=0,n=t.count;e<n;e++)je.fromBufferAttribute(t,e),je.normalize(),t.setXYZ(e,je.x,je.y,je.z)}toNonIndexed(){function t(o,c){const l=o.array,h=o.itemSize,u=o.normalized,d=new l.constructor(c.length*h);let f=0,g=0;for(let _=0,m=c.length;_<m;_++){o.isInterleavedBufferAttribute?f=c[_]*o.data.stride+o.offset:f=c[_]*h;for(let p=0;p<h;p++)d[g++]=l[f++]}return new bn(d,h,u)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;const e=new Le,n=this.index.array,s=this.attributes;for(const o in s){const c=s[o],l=t(c,n);e.setAttribute(o,l)}const r=this.morphAttributes;for(const o in r){const c=[],l=r[o];for(let h=0,u=l.length;h<u;h++){const d=l[h],f=t(d,n);c.push(f)}e.morphAttributes[o]=c}e.morphTargetsRelative=this.morphTargetsRelative;const a=this.groups;for(let o=0,c=a.length;o<c;o++){const l=a[o];e.addGroup(l.start,l.count,l.materialIndex)}return e}toJSON(){const t={metadata:{version:4.6,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(t.uuid=this.uuid,t.type=this.type,this.name!==""&&(t.name=this.name),Object.keys(this.userData).length>0&&(t.userData=this.userData),this.parameters!==void 0){const c=this.parameters;for(const l in c)c[l]!==void 0&&(t[l]=c[l]);return t}t.data={attributes:{}};const e=this.index;e!==null&&(t.data.index={type:e.array.constructor.name,array:Array.prototype.slice.call(e.array)});const n=this.attributes;for(const c in n){const l=n[c];t.data.attributes[c]=l.toJSON(t.data)}const s={};let r=!1;for(const c in this.morphAttributes){const l=this.morphAttributes[c],h=[];for(let u=0,d=l.length;u<d;u++){const f=l[u];h.push(f.toJSON(t.data))}h.length>0&&(s[c]=h,r=!0)}r&&(t.data.morphAttributes=s,t.data.morphTargetsRelative=this.morphTargetsRelative);const a=this.groups;a.length>0&&(t.data.groups=JSON.parse(JSON.stringify(a)));const o=this.boundingSphere;return o!==null&&(t.data.boundingSphere={center:o.center.toArray(),radius:o.radius}),t}clone(){return new this.constructor().copy(this)}copy(t){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;const e={};this.name=t.name;const n=t.index;n!==null&&this.setIndex(n.clone(e));const s=t.attributes;for(const l in s){const h=s[l];this.setAttribute(l,h.clone(e))}const r=t.morphAttributes;for(const l in r){const h=[],u=r[l];for(let d=0,f=u.length;d<f;d++)h.push(u[d].clone(e));this.morphAttributes[l]=h}this.morphTargetsRelative=t.morphTargetsRelative;const a=t.groups;for(let l=0,h=a.length;l<h;l++){const u=a[l];this.addGroup(u.start,u.count,u.materialIndex)}const o=t.boundingBox;o!==null&&(this.boundingBox=o.clone());const c=t.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=t.drawRange.start,this.drawRange.count=t.drawRange.count,this.userData=t.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}}const Vl=new Yt,Vi=new Gs,Gr=new gi,Hl=new D,Wr=new D,Xr=new D,qr=new D,So=new D,jr=new D,Gl=new D,Yr=new D;class ge extends De{constructor(t=new Le,e=new Ke){super(),this.isMesh=!0,this.type="Mesh",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),t.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=t.morphTargetInfluences.slice()),t.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},t.morphTargetDictionary)),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}getVertexPosition(t,e){const n=this.geometry,s=n.attributes.position,r=n.morphAttributes.position,a=n.morphTargetsRelative;e.fromBufferAttribute(s,t);const o=this.morphTargetInfluences;if(r&&o){jr.set(0,0,0);for(let c=0,l=r.length;c<l;c++){const h=o[c],u=r[c];h!==0&&(So.fromBufferAttribute(u,t),a?jr.addScaledVector(So,h):jr.addScaledVector(So.sub(e),h))}e.add(jr)}return e}raycast(t,e){const n=this.geometry,s=this.material,r=this.matrixWorld;s!==void 0&&(n.boundingSphere===null&&n.computeBoundingSphere(),Gr.copy(n.boundingSphere),Gr.applyMatrix4(r),Vi.copy(t.ray).recast(t.near),!(Gr.containsPoint(Vi.origin)===!1&&(Vi.intersectSphere(Gr,Hl)===null||Vi.origin.distanceToSquared(Hl)>(t.far-t.near)**2))&&(Vl.copy(r).invert(),Vi.copy(t.ray).applyMatrix4(Vl),!(n.boundingBox!==null&&Vi.intersectsBox(n.boundingBox)===!1)&&this._computeIntersections(t,e,Vi)))}_computeIntersections(t,e,n){let s;const r=this.geometry,a=this.material,o=r.index,c=r.attributes.position,l=r.attributes.uv,h=r.attributes.uv1,u=r.attributes.normal,d=r.groups,f=r.drawRange;if(o!==null)if(Array.isArray(a))for(let g=0,_=d.length;g<_;g++){const m=d[g],p=a[m.materialIndex],P=Math.max(m.start,f.start),w=Math.min(o.count,Math.min(m.start+m.count,f.start+f.count));for(let y=P,N=w;y<N;y+=3){const C=o.getX(y),L=o.getX(y+1),I=o.getX(y+2);s=$r(this,p,t,n,l,h,u,C,L,I),s&&(s.faceIndex=Math.floor(y/3),s.face.materialIndex=m.materialIndex,e.push(s))}}else{const g=Math.max(0,f.start),_=Math.min(o.count,f.start+f.count);for(let m=g,p=_;m<p;m+=3){const P=o.getX(m),w=o.getX(m+1),y=o.getX(m+2);s=$r(this,a,t,n,l,h,u,P,w,y),s&&(s.faceIndex=Math.floor(m/3),e.push(s))}}else if(c!==void 0)if(Array.isArray(a))for(let g=0,_=d.length;g<_;g++){const m=d[g],p=a[m.materialIndex],P=Math.max(m.start,f.start),w=Math.min(c.count,Math.min(m.start+m.count,f.start+f.count));for(let y=P,N=w;y<N;y+=3){const C=y,L=y+1,I=y+2;s=$r(this,p,t,n,l,h,u,C,L,I),s&&(s.faceIndex=Math.floor(y/3),s.face.materialIndex=m.materialIndex,e.push(s))}}else{const g=Math.max(0,f.start),_=Math.min(c.count,f.start+f.count);for(let m=g,p=_;m<p;m+=3){const P=m,w=m+1,y=m+2;s=$r(this,a,t,n,l,h,u,P,w,y),s&&(s.faceIndex=Math.floor(m/3),e.push(s))}}}}function qf(i,t,e,n,s,r,a,o){let c;if(t.side===fn?c=n.intersectTriangle(a,r,s,!0,o):c=n.intersectTriangle(s,r,a,t.side===di,o),c===null)return null;Yr.copy(o),Yr.applyMatrix4(i.matrixWorld);const l=e.ray.origin.distanceTo(Yr);return l<e.near||l>e.far?null:{distance:l,point:Yr.clone(),object:i}}function $r(i,t,e,n,s,r,a,o,c,l){i.getVertexPosition(o,Wr),i.getVertexPosition(c,Xr),i.getVertexPosition(l,qr);const h=qf(i,t,e,n,Wr,Xr,qr,Gl);if(h){const u=new D;kn.getBarycoord(Gl,Wr,Xr,qr,u),s&&(h.uv=kn.getInterpolatedAttribute(s,o,c,l,u,new At)),r&&(h.uv1=kn.getInterpolatedAttribute(r,o,c,l,u,new At)),a&&(h.normal=kn.getInterpolatedAttribute(a,o,c,l,u,new D),h.normal.dot(n.direction)>0&&h.normal.multiplyScalar(-1));const d={a:o,b:c,c:l,normal:new D,materialIndex:0};kn.getNormal(Wr,Xr,qr,d.normal),h.face=d,h.barycoord=u}return h}class Ws extends Le{constructor(t=1,e=1,n=1,s=1,r=1,a=1){super(),this.type="BoxGeometry",this.parameters={width:t,height:e,depth:n,widthSegments:s,heightSegments:r,depthSegments:a};const o=this;s=Math.floor(s),r=Math.floor(r),a=Math.floor(a);const c=[],l=[],h=[],u=[];let d=0,f=0;g("z","y","x",-1,-1,n,e,t,a,r,0),g("z","y","x",1,-1,n,e,-t,a,r,1),g("x","z","y",1,1,t,n,e,s,a,2),g("x","z","y",1,-1,t,n,-e,s,a,3),g("x","y","z",1,-1,t,e,n,s,r,4),g("x","y","z",-1,-1,t,e,-n,s,r,5),this.setIndex(c),this.setAttribute("position",new ie(l,3)),this.setAttribute("normal",new ie(h,3)),this.setAttribute("uv",new ie(u,2));function g(_,m,p,P,w,y,N,C,L,I,M){const b=y/L,F=N/I,k=y/2,H=N/2,Z=C/2,tt=L+1,O=I+1;let et=0,W=0;const lt=new D;for(let pt=0;pt<O;pt++){const mt=pt*F-H;for(let Rt=0;Rt<tt;Rt++){const wt=Rt*b-k;lt[_]=wt*P,lt[m]=mt*w,lt[p]=Z,l.push(lt.x,lt.y,lt.z),lt[_]=0,lt[m]=0,lt[p]=C>0?1:-1,h.push(lt.x,lt.y,lt.z),u.push(Rt/L),u.push(1-pt/I),et+=1}}for(let pt=0;pt<I;pt++)for(let mt=0;mt<L;mt++){const Rt=d+mt+tt*pt,wt=d+mt+tt*(pt+1),q=d+(mt+1)+tt*(pt+1),J=d+(mt+1)+tt*pt;c.push(Rt,wt,J),c.push(wt,q,J),W+=6}o.addGroup(f,W,M),f+=W,d+=et}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Ws(t.width,t.height,t.depth,t.widthSegments,t.heightSegments,t.depthSegments)}}function Us(i){const t={};for(const e in i){t[e]={};for(const n in i[e]){const s=i[e][n];s&&(s.isColor||s.isMatrix3||s.isMatrix4||s.isVector2||s.isVector3||s.isVector4||s.isTexture||s.isQuaternion)?s.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),t[e][n]=null):t[e][n]=s.clone():Array.isArray(s)?t[e][n]=s.slice():t[e][n]=s}}return t}function rn(i){const t={};for(let e=0;e<i.length;e++){const n=Us(i[e]);for(const s in n)t[s]=n[s]}return t}function jf(i){const t=[];for(let e=0;e<i.length;e++)t.push(i[e].clone());return t}function bu(i){const t=i.getRenderTarget();return t===null?i.outputColorSpace:t.isXRRenderTarget===!0?t.texture.colorSpace:le.workingColorSpace}const Yf={clone:Us,merge:rn};var $f=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,Kf=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;class Ni extends Hn{static get type(){return"ShaderMaterial"}constructor(t){super(),this.isShaderMaterial=!0,this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=$f,this.fragmentShader=Kf,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,t!==void 0&&this.setValues(t)}copy(t){return super.copy(t),this.fragmentShader=t.fragmentShader,this.vertexShader=t.vertexShader,this.uniforms=Us(t.uniforms),this.uniformsGroups=jf(t.uniformsGroups),this.defines=Object.assign({},t.defines),this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.fog=t.fog,this.lights=t.lights,this.clipping=t.clipping,this.extensions=Object.assign({},t.extensions),this.glslVersion=t.glslVersion,this}toJSON(t){const e=super.toJSON(t);e.glslVersion=this.glslVersion,e.uniforms={};for(const s in this.uniforms){const a=this.uniforms[s].value;a&&a.isTexture?e.uniforms[s]={type:"t",value:a.toJSON(t).uuid}:a&&a.isColor?e.uniforms[s]={type:"c",value:a.getHex()}:a&&a.isVector2?e.uniforms[s]={type:"v2",value:a.toArray()}:a&&a.isVector3?e.uniforms[s]={type:"v3",value:a.toArray()}:a&&a.isVector4?e.uniforms[s]={type:"v4",value:a.toArray()}:a&&a.isMatrix3?e.uniforms[s]={type:"m3",value:a.toArray()}:a&&a.isMatrix4?e.uniforms[s]={type:"m4",value:a.toArray()}:e.uniforms[s]={value:a}}Object.keys(this.defines).length>0&&(e.defines=this.defines),e.vertexShader=this.vertexShader,e.fragmentShader=this.fragmentShader,e.lights=this.lights,e.clipping=this.clipping;const n={};for(const s in this.extensions)this.extensions[s]===!0&&(n[s]=!0);return Object.keys(n).length>0&&(e.extensions=n),e}}class Su extends De{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Yt,this.projectionMatrix=new Yt,this.projectionMatrixInverse=new Yt,this.coordinateSystem=hi}copy(t,e){return super.copy(t,e),this.matrixWorldInverse.copy(t.matrixWorldInverse),this.projectionMatrix.copy(t.projectionMatrix),this.projectionMatrixInverse.copy(t.projectionMatrixInverse),this.coordinateSystem=t.coordinateSystem,this}getWorldDirection(t){return super.getWorldDirection(t).negate()}updateMatrixWorld(t){super.updateMatrixWorld(t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(t,e){super.updateWorldMatrix(t,e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}}const Ei=new D,Wl=new At,Xl=new At;class tn extends Su{constructor(t=50,e=1,n=.1,s=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=t,this.zoom=1,this.near=n,this.far=s,this.focus=10,this.aspect=e,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.fov=t.fov,this.zoom=t.zoom,this.near=t.near,this.far=t.far,this.focus=t.focus,this.aspect=t.aspect,this.view=t.view===null?null:Object.assign({},t.view),this.filmGauge=t.filmGauge,this.filmOffset=t.filmOffset,this}setFocalLength(t){const e=.5*this.getFilmHeight()/t;this.fov=Is*2*Math.atan(e),this.updateProjectionMatrix()}getFocalLength(){const t=Math.tan(lr*.5*this.fov);return .5*this.getFilmHeight()/t}getEffectiveFOV(){return Is*2*Math.atan(Math.tan(lr*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(t,e,n){Ei.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),e.set(Ei.x,Ei.y).multiplyScalar(-t/Ei.z),Ei.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),n.set(Ei.x,Ei.y).multiplyScalar(-t/Ei.z)}getViewSize(t,e){return this.getViewBounds(t,Wl,Xl),e.subVectors(Xl,Wl)}setViewOffset(t,e,n,s,r,a){this.aspect=t/e,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=this.near;let e=t*Math.tan(lr*.5*this.fov)/this.zoom,n=2*e,s=this.aspect*n,r=-.5*s;const a=this.view;if(this.view!==null&&this.view.enabled){const c=a.fullWidth,l=a.fullHeight;r+=a.offsetX*s/c,e-=a.offsetY*n/l,s*=a.width/c,n*=a.height/l}const o=this.filmOffset;o!==0&&(r+=t*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+s,e,e-n,t,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.fov=this.fov,e.object.zoom=this.zoom,e.object.near=this.near,e.object.far=this.far,e.object.focus=this.focus,e.object.aspect=this.aspect,this.view!==null&&(e.object.view=Object.assign({},this.view)),e.object.filmGauge=this.filmGauge,e.object.filmOffset=this.filmOffset,e}}const gs=-90,_s=1;class Jf extends De{constructor(t,e,n){super(),this.type="CubeCamera",this.renderTarget=n,this.coordinateSystem=null,this.activeMipmapLevel=0;const s=new tn(gs,_s,t,e);s.layers=this.layers,this.add(s);const r=new tn(gs,_s,t,e);r.layers=this.layers,this.add(r);const a=new tn(gs,_s,t,e);a.layers=this.layers,this.add(a);const o=new tn(gs,_s,t,e);o.layers=this.layers,this.add(o);const c=new tn(gs,_s,t,e);c.layers=this.layers,this.add(c);const l=new tn(gs,_s,t,e);l.layers=this.layers,this.add(l)}updateCoordinateSystem(){const t=this.coordinateSystem,e=this.children.concat(),[n,s,r,a,o,c]=e;for(const l of e)this.remove(l);if(t===hi)n.up.set(0,1,0),n.lookAt(1,0,0),s.up.set(0,1,0),s.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),c.up.set(0,1,0),c.lookAt(0,0,-1);else if(t===Sa)n.up.set(0,-1,0),n.lookAt(-1,0,0),s.up.set(0,-1,0),s.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),c.up.set(0,-1,0),c.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+t);for(const l of e)this.add(l),l.updateMatrixWorld()}update(t,e){this.parent===null&&this.updateMatrixWorld();const{renderTarget:n,activeMipmapLevel:s}=this;this.coordinateSystem!==t.coordinateSystem&&(this.coordinateSystem=t.coordinateSystem,this.updateCoordinateSystem());const[r,a,o,c,l,h]=this.children,u=t.getRenderTarget(),d=t.getActiveCubeFace(),f=t.getActiveMipmapLevel(),g=t.xr.enabled;t.xr.enabled=!1;const _=n.texture.generateMipmaps;n.texture.generateMipmaps=!1,t.setRenderTarget(n,0,s),t.render(e,r),t.setRenderTarget(n,1,s),t.render(e,a),t.setRenderTarget(n,2,s),t.render(e,o),t.setRenderTarget(n,3,s),t.render(e,c),t.setRenderTarget(n,4,s),t.render(e,l),n.texture.generateMipmaps=_,t.setRenderTarget(n,5,s),t.render(e,h),t.setRenderTarget(u,d,f),t.xr.enabled=g,n.texture.needsPMREMUpdate=!0}}class Eu extends Je{constructor(t,e,n,s,r,a,o,c,l,h){t=t!==void 0?t:[],e=e!==void 0?e:Ps,super(t,e,n,s,r,a,o,c,l,h),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(t){this.image=t}}class Zf extends Ji{constructor(t=1,e={}){super(t,t,e),this.isWebGLCubeRenderTarget=!0;const n={width:t,height:t,depth:1},s=[n,n,n,n,n,n];this.texture=new Eu(s,e.mapping,e.wrapS,e.wrapT,e.magFilter,e.minFilter,e.format,e.type,e.anisotropy,e.colorSpace),this.texture.isRenderTargetTexture=!0,this.texture.generateMipmaps=e.generateMipmaps!==void 0?e.generateMipmaps:!1,this.texture.minFilter=e.minFilter!==void 0?e.minFilter:xn}fromEquirectangularTexture(t,e){this.texture.type=e.type,this.texture.colorSpace=e.colorSpace,this.texture.generateMipmaps=e.generateMipmaps,this.texture.minFilter=e.minFilter,this.texture.magFilter=e.magFilter;const n={uniforms:{tEquirect:{value:null}},vertexShader:`

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
			`},s=new Ws(5,5,5),r=new Ni({name:"CubemapFromEquirect",uniforms:Us(n.uniforms),vertexShader:n.vertexShader,fragmentShader:n.fragmentShader,side:fn,blending:Pi});r.uniforms.tEquirect.value=e;const a=new ge(s,r),o=e.minFilter;return e.minFilter===li&&(e.minFilter=xn),new Jf(1,10,this).update(t,a),e.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(t,e,n,s){const r=t.getRenderTarget();for(let a=0;a<6;a++)t.setRenderTarget(this,a),t.clear(e,n,s);t.setRenderTarget(r)}}const Eo=new D,Qf=new D,tp=new re;class ci{constructor(t=new D(1,0,0),e=0){this.isPlane=!0,this.normal=t,this.constant=e}set(t,e){return this.normal.copy(t),this.constant=e,this}setComponents(t,e,n,s){return this.normal.set(t,e,n),this.constant=s,this}setFromNormalAndCoplanarPoint(t,e){return this.normal.copy(t),this.constant=-e.dot(this.normal),this}setFromCoplanarPoints(t,e,n){const s=Eo.subVectors(n,e).cross(Qf.subVectors(t,e)).normalize();return this.setFromNormalAndCoplanarPoint(s,t),this}copy(t){return this.normal.copy(t.normal),this.constant=t.constant,this}normalize(){const t=1/this.normal.length();return this.normal.multiplyScalar(t),this.constant*=t,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(t){return this.normal.dot(t)+this.constant}distanceToSphere(t){return this.distanceToPoint(t.center)-t.radius}projectPoint(t,e){return e.copy(t).addScaledVector(this.normal,-this.distanceToPoint(t))}intersectLine(t,e){const n=t.delta(Eo),s=this.normal.dot(n);if(s===0)return this.distanceToPoint(t.start)===0?e.copy(t.start):null;const r=-(t.start.dot(this.normal)+this.constant)/s;return r<0||r>1?null:e.copy(t.start).addScaledVector(n,r)}intersectsLine(t){const e=this.distanceToPoint(t.start),n=this.distanceToPoint(t.end);return e<0&&n>0||n<0&&e>0}intersectsBox(t){return t.intersectsPlane(this)}intersectsSphere(t){return t.intersectsPlane(this)}coplanarPoint(t){return t.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(t,e){const n=e||tp.getNormalMatrix(t),s=this.coplanarPoint(Eo).applyMatrix4(t),r=this.normal.applyMatrix3(n).normalize();return this.constant=-s.dot(r),this}translate(t){return this.constant-=t.dot(this.normal),this}equals(t){return t.normal.equals(this.normal)&&t.constant===this.constant}clone(){return new this.constructor().copy(this)}}const Hi=new gi,Kr=new D;class Yc{constructor(t=new ci,e=new ci,n=new ci,s=new ci,r=new ci,a=new ci){this.planes=[t,e,n,s,r,a]}set(t,e,n,s,r,a){const o=this.planes;return o[0].copy(t),o[1].copy(e),o[2].copy(n),o[3].copy(s),o[4].copy(r),o[5].copy(a),this}copy(t){const e=this.planes;for(let n=0;n<6;n++)e[n].copy(t.planes[n]);return this}setFromProjectionMatrix(t,e=hi){const n=this.planes,s=t.elements,r=s[0],a=s[1],o=s[2],c=s[3],l=s[4],h=s[5],u=s[6],d=s[7],f=s[8],g=s[9],_=s[10],m=s[11],p=s[12],P=s[13],w=s[14],y=s[15];if(n[0].setComponents(c-r,d-l,m-f,y-p).normalize(),n[1].setComponents(c+r,d+l,m+f,y+p).normalize(),n[2].setComponents(c+a,d+h,m+g,y+P).normalize(),n[3].setComponents(c-a,d-h,m-g,y-P).normalize(),n[4].setComponents(c-o,d-u,m-_,y-w).normalize(),e===hi)n[5].setComponents(c+o,d+u,m+_,y+w).normalize();else if(e===Sa)n[5].setComponents(o,u,_,w).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+e);return this}intersectsObject(t){if(t.boundingSphere!==void 0)t.boundingSphere===null&&t.computeBoundingSphere(),Hi.copy(t.boundingSphere).applyMatrix4(t.matrixWorld);else{const e=t.geometry;e.boundingSphere===null&&e.computeBoundingSphere(),Hi.copy(e.boundingSphere).applyMatrix4(t.matrixWorld)}return this.intersectsSphere(Hi)}intersectsSprite(t){return Hi.center.set(0,0,0),Hi.radius=.7071067811865476,Hi.applyMatrix4(t.matrixWorld),this.intersectsSphere(Hi)}intersectsSphere(t){const e=this.planes,n=t.center,s=-t.radius;for(let r=0;r<6;r++)if(e[r].distanceToPoint(n)<s)return!1;return!0}intersectsBox(t){const e=this.planes;for(let n=0;n<6;n++){const s=e[n];if(Kr.x=s.normal.x>0?t.max.x:t.min.x,Kr.y=s.normal.y>0?t.max.y:t.min.y,Kr.z=s.normal.z>0?t.max.z:t.min.z,s.distanceToPoint(Kr)<0)return!1}return!0}containsPoint(t){const e=this.planes;for(let n=0;n<6;n++)if(e[n].distanceToPoint(t)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}}function wu(){let i=null,t=!1,e=null,n=null;function s(r,a){e(r,a),n=i.requestAnimationFrame(s)}return{start:function(){t!==!0&&e!==null&&(n=i.requestAnimationFrame(s),t=!0)},stop:function(){i.cancelAnimationFrame(n),t=!1},setAnimationLoop:function(r){e=r},setContext:function(r){i=r}}}function ep(i){const t=new WeakMap;function e(o,c){const l=o.array,h=o.usage,u=l.byteLength,d=i.createBuffer();i.bindBuffer(c,d),i.bufferData(c,l,h),o.onUploadCallback();let f;if(l instanceof Float32Array)f=i.FLOAT;else if(l instanceof Uint16Array)o.isFloat16BufferAttribute?f=i.HALF_FLOAT:f=i.UNSIGNED_SHORT;else if(l instanceof Int16Array)f=i.SHORT;else if(l instanceof Uint32Array)f=i.UNSIGNED_INT;else if(l instanceof Int32Array)f=i.INT;else if(l instanceof Int8Array)f=i.BYTE;else if(l instanceof Uint8Array)f=i.UNSIGNED_BYTE;else if(l instanceof Uint8ClampedArray)f=i.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+l);return{buffer:d,type:f,bytesPerElement:l.BYTES_PER_ELEMENT,version:o.version,size:u}}function n(o,c,l){const h=c.array,u=c.updateRanges;if(i.bindBuffer(l,o),u.length===0)i.bufferSubData(l,0,h);else{u.sort((f,g)=>f.start-g.start);let d=0;for(let f=1;f<u.length;f++){const g=u[d],_=u[f];_.start<=g.start+g.count+1?g.count=Math.max(g.count,_.start+_.count-g.start):(++d,u[d]=_)}u.length=d+1;for(let f=0,g=u.length;f<g;f++){const _=u[f];i.bufferSubData(l,_.start*h.BYTES_PER_ELEMENT,h,_.start,_.count)}c.clearUpdateRanges()}c.onUploadCallback()}function s(o){return o.isInterleavedBufferAttribute&&(o=o.data),t.get(o)}function r(o){o.isInterleavedBufferAttribute&&(o=o.data);const c=t.get(o);c&&(i.deleteBuffer(c.buffer),t.delete(o))}function a(o,c){if(o.isInterleavedBufferAttribute&&(o=o.data),o.isGLBufferAttribute){const h=t.get(o);(!h||h.version<o.version)&&t.set(o,{buffer:o.buffer,type:o.type,bytesPerElement:o.elementSize,version:o.version});return}const l=t.get(o);if(l===void 0)t.set(o,e(o,c));else if(l.version<o.version){if(l.size!==o.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");n(l.buffer,o,c),l.version=o.version}}return{get:s,remove:r,update:a}}class Ha extends Le{constructor(t=1,e=1,n=1,s=1){super(),this.type="PlaneGeometry",this.parameters={width:t,height:e,widthSegments:n,heightSegments:s};const r=t/2,a=e/2,o=Math.floor(n),c=Math.floor(s),l=o+1,h=c+1,u=t/o,d=e/c,f=[],g=[],_=[],m=[];for(let p=0;p<h;p++){const P=p*d-a;for(let w=0;w<l;w++){const y=w*u-r;g.push(y,-P,0),_.push(0,0,1),m.push(w/o),m.push(1-p/c)}}for(let p=0;p<c;p++)for(let P=0;P<o;P++){const w=P+l*p,y=P+l*(p+1),N=P+1+l*(p+1),C=P+1+l*p;f.push(w,y,C),f.push(y,N,C)}this.setIndex(f),this.setAttribute("position",new ie(g,3)),this.setAttribute("normal",new ie(_,3)),this.setAttribute("uv",new ie(m,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Ha(t.width,t.height,t.widthSegments,t.heightSegments)}}var np=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,ip=`#ifdef USE_ALPHAHASH
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
#endif`,sp=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,rp=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,ap=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,op=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,cp=`#ifdef USE_AOMAP
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
#endif`,lp=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,hp=`#ifdef USE_BATCHING
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
#endif`,up=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,dp=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,fp=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,pp=`float G_BlinnPhong_Implicit( ) {
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
} // validated`,mp=`#ifdef USE_IRIDESCENCE
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
#endif`,gp=`#ifdef USE_BUMPMAP
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
#endif`,_p=`#if NUM_CLIPPING_PLANES > 0
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
#endif`,vp=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,xp=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,yp=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,Mp=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,bp=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,Sp=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,Ep=`#if defined( USE_COLOR_ALPHA )
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
#endif`,wp=`#define PI 3.141592653589793
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
} // validated`,Tp=`#ifdef ENVMAP_TYPE_CUBE_UV
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
#endif`,Ap=`vec3 transformedNormal = objectNormal;
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
#endif`,Cp=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,Rp=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,Pp=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,Lp=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Np="gl_FragColor = linearToOutputTexel( gl_FragColor );",Dp=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,Ip=`#ifdef USE_ENVMAP
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
#endif`,Up=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Fp=`#ifdef USE_ENVMAP
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
#endif`,Op=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,kp=`#ifdef USE_ENVMAP
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
#endif`,Bp=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,zp=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,Vp=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,Hp=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,Gp=`#ifdef USE_GRADIENTMAP
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
}`,Wp=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,Xp=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,qp=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,jp=`uniform bool receiveShadow;
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
#endif`,Yp=`#ifdef USE_ENVMAP
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
#endif`,$p=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,Kp=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,Jp=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,Zp=`varying vec3 vViewPosition;
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
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,Qp=`PhysicalMaterial material;
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
#endif`,tm=`struct PhysicalMaterial {
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
}`,em=`
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
#endif`,nm=`#if defined( RE_IndirectDiffuse )
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
#endif`,im=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,sm=`#if defined( USE_LOGDEPTHBUF )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,rm=`#if defined( USE_LOGDEPTHBUF )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,am=`#ifdef USE_LOGDEPTHBUF
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,om=`#ifdef USE_LOGDEPTHBUF
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,cm=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,lm=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,hm=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
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
#endif`,um=`#if defined( USE_POINTS_UV )
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
#endif`,dm=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,fm=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,pm=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,mm=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,gm=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,_m=`#ifdef USE_MORPHTARGETS
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
#endif`,vm=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,xm=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
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
vec3 nonPerturbedNormal = normal;`,ym=`#ifdef USE_NORMALMAP_OBJECTSPACE
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
#endif`,Mm=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,bm=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,Sm=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,Em=`#ifdef USE_NORMALMAP
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
#endif`,wm=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,Tm=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,Am=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,Cm=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,Rm=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,Pm=`vec3 packNormalToRGB( const in vec3 normal ) {
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
}`,Lm=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Nm=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,Dm=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Im=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,Um=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Fm=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Om=`#if NUM_SPOT_LIGHT_COORDS > 0
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
#endif`,km=`#if NUM_SPOT_LIGHT_COORDS > 0
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
#endif`,Bm=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
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
#endif`,zm=`float getShadowMask() {
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
}`,Vm=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,Hm=`#ifdef USE_SKINNING
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
#endif`,Gm=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,Wm=`#ifdef USE_SKINNING
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
#endif`,Xm=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,qm=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,jm=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,Ym=`#ifndef saturate
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
vec3 CustomToneMapping( vec3 color ) { return color; }`,$m=`#ifdef USE_TRANSMISSION
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
#endif`,Km=`#ifdef USE_TRANSMISSION
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
#endif`,Jm=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,Zm=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,Qm=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
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
#endif`,tg=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;const eg=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,ng=`uniform sampler2D t2D;
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
}`,ig=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,sg=`#ifdef ENVMAP_TYPE_CUBE
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
}`,rg=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,ag=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,og=`#include <common>
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
}`,cg=`#if DEPTH_PACKING == 3200
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
}`,lg=`#define DISTANCE
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
}`,hg=`#define DISTANCE
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
}`,ug=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,dg=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,fg=`uniform float scale;
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
}`,pg=`uniform vec3 diffuse;
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
}`,mg=`#include <common>
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
}`,gg=`uniform vec3 diffuse;
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
}`,_g=`#define LAMBERT
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
}`,vg=`#define LAMBERT
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
}`,xg=`#define MATCAP
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
}`,yg=`#define MATCAP
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
}`,Mg=`#define NORMAL
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
}`,bg=`#define NORMAL
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
}`,Sg=`#define PHONG
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
}`,Eg=`#define PHONG
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
}`,wg=`#define STANDARD
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
}`,Tg=`#define STANDARD
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
}`,Ag=`#define TOON
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
}`,Cg=`#define TOON
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
}`,Rg=`uniform float size;
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
}`,Pg=`uniform vec3 diffuse;
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
}`,Lg=`#include <common>
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
}`,Ng=`uniform vec3 color;
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
}`,Dg=`uniform float rotation;
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
}`,Ig=`uniform vec3 diffuse;
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
}`,ae={alphahash_fragment:np,alphahash_pars_fragment:ip,alphamap_fragment:sp,alphamap_pars_fragment:rp,alphatest_fragment:ap,alphatest_pars_fragment:op,aomap_fragment:cp,aomap_pars_fragment:lp,batching_pars_vertex:hp,batching_vertex:up,begin_vertex:dp,beginnormal_vertex:fp,bsdfs:pp,iridescence_fragment:mp,bumpmap_pars_fragment:gp,clipping_planes_fragment:_p,clipping_planes_pars_fragment:vp,clipping_planes_pars_vertex:xp,clipping_planes_vertex:yp,color_fragment:Mp,color_pars_fragment:bp,color_pars_vertex:Sp,color_vertex:Ep,common:wp,cube_uv_reflection_fragment:Tp,defaultnormal_vertex:Ap,displacementmap_pars_vertex:Cp,displacementmap_vertex:Rp,emissivemap_fragment:Pp,emissivemap_pars_fragment:Lp,colorspace_fragment:Np,colorspace_pars_fragment:Dp,envmap_fragment:Ip,envmap_common_pars_fragment:Up,envmap_pars_fragment:Fp,envmap_pars_vertex:Op,envmap_physical_pars_fragment:Yp,envmap_vertex:kp,fog_vertex:Bp,fog_pars_vertex:zp,fog_fragment:Vp,fog_pars_fragment:Hp,gradientmap_pars_fragment:Gp,lightmap_pars_fragment:Wp,lights_lambert_fragment:Xp,lights_lambert_pars_fragment:qp,lights_pars_begin:jp,lights_toon_fragment:$p,lights_toon_pars_fragment:Kp,lights_phong_fragment:Jp,lights_phong_pars_fragment:Zp,lights_physical_fragment:Qp,lights_physical_pars_fragment:tm,lights_fragment_begin:em,lights_fragment_maps:nm,lights_fragment_end:im,logdepthbuf_fragment:sm,logdepthbuf_pars_fragment:rm,logdepthbuf_pars_vertex:am,logdepthbuf_vertex:om,map_fragment:cm,map_pars_fragment:lm,map_particle_fragment:hm,map_particle_pars_fragment:um,metalnessmap_fragment:dm,metalnessmap_pars_fragment:fm,morphinstance_vertex:pm,morphcolor_vertex:mm,morphnormal_vertex:gm,morphtarget_pars_vertex:_m,morphtarget_vertex:vm,normal_fragment_begin:xm,normal_fragment_maps:ym,normal_pars_fragment:Mm,normal_pars_vertex:bm,normal_vertex:Sm,normalmap_pars_fragment:Em,clearcoat_normal_fragment_begin:wm,clearcoat_normal_fragment_maps:Tm,clearcoat_pars_fragment:Am,iridescence_pars_fragment:Cm,opaque_fragment:Rm,packing:Pm,premultiplied_alpha_fragment:Lm,project_vertex:Nm,dithering_fragment:Dm,dithering_pars_fragment:Im,roughnessmap_fragment:Um,roughnessmap_pars_fragment:Fm,shadowmap_pars_fragment:Om,shadowmap_pars_vertex:km,shadowmap_vertex:Bm,shadowmask_pars_fragment:zm,skinbase_vertex:Vm,skinning_pars_vertex:Hm,skinning_vertex:Gm,skinnormal_vertex:Wm,specularmap_fragment:Xm,specularmap_pars_fragment:qm,tonemapping_fragment:jm,tonemapping_pars_fragment:Ym,transmission_fragment:$m,transmission_pars_fragment:Km,uv_pars_fragment:Jm,uv_pars_vertex:Zm,uv_vertex:Qm,worldpos_vertex:tg,background_vert:eg,background_frag:ng,backgroundCube_vert:ig,backgroundCube_frag:sg,cube_vert:rg,cube_frag:ag,depth_vert:og,depth_frag:cg,distanceRGBA_vert:lg,distanceRGBA_frag:hg,equirect_vert:ug,equirect_frag:dg,linedashed_vert:fg,linedashed_frag:pg,meshbasic_vert:mg,meshbasic_frag:gg,meshlambert_vert:_g,meshlambert_frag:vg,meshmatcap_vert:xg,meshmatcap_frag:yg,meshnormal_vert:Mg,meshnormal_frag:bg,meshphong_vert:Sg,meshphong_frag:Eg,meshphysical_vert:wg,meshphysical_frag:Tg,meshtoon_vert:Ag,meshtoon_frag:Cg,points_vert:Rg,points_frag:Pg,shadow_vert:Lg,shadow_frag:Ng,sprite_vert:Dg,sprite_frag:Ig},_t={common:{diffuse:{value:new Jt(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new re},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new re}},envmap:{envMap:{value:null},envMapRotation:{value:new re},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new re}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new re}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new re},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new re},normalScale:{value:new At(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new re},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new re}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new re}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new re}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Jt(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new Jt(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0},uvTransform:{value:new re}},sprite:{diffuse:{value:new Jt(16777215)},opacity:{value:1},center:{value:new At(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new re},alphaMap:{value:null},alphaMapTransform:{value:new re},alphaTest:{value:0}}},Xn={basic:{uniforms:rn([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.fog]),vertexShader:ae.meshbasic_vert,fragmentShader:ae.meshbasic_frag},lambert:{uniforms:rn([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,_t.lights,{emissive:{value:new Jt(0)}}]),vertexShader:ae.meshlambert_vert,fragmentShader:ae.meshlambert_frag},phong:{uniforms:rn([_t.common,_t.specularmap,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,_t.lights,{emissive:{value:new Jt(0)},specular:{value:new Jt(1118481)},shininess:{value:30}}]),vertexShader:ae.meshphong_vert,fragmentShader:ae.meshphong_frag},standard:{uniforms:rn([_t.common,_t.envmap,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.roughnessmap,_t.metalnessmap,_t.fog,_t.lights,{emissive:{value:new Jt(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:ae.meshphysical_vert,fragmentShader:ae.meshphysical_frag},toon:{uniforms:rn([_t.common,_t.aomap,_t.lightmap,_t.emissivemap,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.gradientmap,_t.fog,_t.lights,{emissive:{value:new Jt(0)}}]),vertexShader:ae.meshtoon_vert,fragmentShader:ae.meshtoon_frag},matcap:{uniforms:rn([_t.common,_t.bumpmap,_t.normalmap,_t.displacementmap,_t.fog,{matcap:{value:null}}]),vertexShader:ae.meshmatcap_vert,fragmentShader:ae.meshmatcap_frag},points:{uniforms:rn([_t.points,_t.fog]),vertexShader:ae.points_vert,fragmentShader:ae.points_frag},dashed:{uniforms:rn([_t.common,_t.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:ae.linedashed_vert,fragmentShader:ae.linedashed_frag},depth:{uniforms:rn([_t.common,_t.displacementmap]),vertexShader:ae.depth_vert,fragmentShader:ae.depth_frag},normal:{uniforms:rn([_t.common,_t.bumpmap,_t.normalmap,_t.displacementmap,{opacity:{value:1}}]),vertexShader:ae.meshnormal_vert,fragmentShader:ae.meshnormal_frag},sprite:{uniforms:rn([_t.sprite,_t.fog]),vertexShader:ae.sprite_vert,fragmentShader:ae.sprite_frag},background:{uniforms:{uvTransform:{value:new re},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:ae.background_vert,fragmentShader:ae.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new re}},vertexShader:ae.backgroundCube_vert,fragmentShader:ae.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:ae.cube_vert,fragmentShader:ae.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:ae.equirect_vert,fragmentShader:ae.equirect_frag},distanceRGBA:{uniforms:rn([_t.common,_t.displacementmap,{referencePosition:{value:new D},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:ae.distanceRGBA_vert,fragmentShader:ae.distanceRGBA_frag},shadow:{uniforms:rn([_t.lights,_t.fog,{color:{value:new Jt(0)},opacity:{value:1}}]),vertexShader:ae.shadow_vert,fragmentShader:ae.shadow_frag}};Xn.physical={uniforms:rn([Xn.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new re},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new re},clearcoatNormalScale:{value:new At(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new re},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new re},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new re},sheen:{value:0},sheenColor:{value:new Jt(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new re},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new re},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new re},transmissionSamplerSize:{value:new At},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new re},attenuationDistance:{value:0},attenuationColor:{value:new Jt(0)},specularColor:{value:new Jt(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new re},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new re},anisotropyVector:{value:new At},anisotropyMap:{value:null},anisotropyMapTransform:{value:new re}}]),vertexShader:ae.meshphysical_vert,fragmentShader:ae.meshphysical_frag};const Jr={r:0,b:0,g:0},Gi=new pn,Ug=new Yt;function Fg(i,t,e,n,s,r,a){const o=new Jt(0);let c=r===!0?0:1,l,h,u=null,d=0,f=null;function g(P){let w=P.isScene===!0?P.background:null;return w&&w.isTexture&&(w=(P.backgroundBlurriness>0?e:t).get(w)),w}function _(P){let w=!1;const y=g(P);y===null?p(o,c):y&&y.isColor&&(p(y,1),w=!0);const N=i.xr.getEnvironmentBlendMode();N==="additive"?n.buffers.color.setClear(0,0,0,1,a):N==="alpha-blend"&&n.buffers.color.setClear(0,0,0,0,a),(i.autoClear||w)&&(n.buffers.depth.setTest(!0),n.buffers.depth.setMask(!0),n.buffers.color.setMask(!0),i.clear(i.autoClearColor,i.autoClearDepth,i.autoClearStencil))}function m(P,w){const y=g(w);y&&(y.isCubeTexture||y.mapping===Ba)?(h===void 0&&(h=new ge(new Ws(1,1,1),new Ni({name:"BackgroundCubeMaterial",uniforms:Us(Xn.backgroundCube.uniforms),vertexShader:Xn.backgroundCube.vertexShader,fragmentShader:Xn.backgroundCube.fragmentShader,side:fn,depthTest:!1,depthWrite:!1,fog:!1})),h.geometry.deleteAttribute("normal"),h.geometry.deleteAttribute("uv"),h.onBeforeRender=function(N,C,L){this.matrixWorld.copyPosition(L.matrixWorld)},Object.defineProperty(h.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),s.update(h)),Gi.copy(w.backgroundRotation),Gi.x*=-1,Gi.y*=-1,Gi.z*=-1,y.isCubeTexture&&y.isRenderTargetTexture===!1&&(Gi.y*=-1,Gi.z*=-1),h.material.uniforms.envMap.value=y,h.material.uniforms.flipEnvMap.value=y.isCubeTexture&&y.isRenderTargetTexture===!1?-1:1,h.material.uniforms.backgroundBlurriness.value=w.backgroundBlurriness,h.material.uniforms.backgroundIntensity.value=w.backgroundIntensity,h.material.uniforms.backgroundRotation.value.setFromMatrix4(Ug.makeRotationFromEuler(Gi)),h.material.toneMapped=le.getTransfer(y.colorSpace)!==we,(u!==y||d!==y.version||f!==i.toneMapping)&&(h.material.needsUpdate=!0,u=y,d=y.version,f=i.toneMapping),h.layers.enableAll(),P.unshift(h,h.geometry,h.material,0,0,null)):y&&y.isTexture&&(l===void 0&&(l=new ge(new Ha(2,2),new Ni({name:"BackgroundMaterial",uniforms:Us(Xn.background.uniforms),vertexShader:Xn.background.vertexShader,fragmentShader:Xn.background.fragmentShader,side:di,depthTest:!1,depthWrite:!1,fog:!1})),l.geometry.deleteAttribute("normal"),Object.defineProperty(l.material,"map",{get:function(){return this.uniforms.t2D.value}}),s.update(l)),l.material.uniforms.t2D.value=y,l.material.uniforms.backgroundIntensity.value=w.backgroundIntensity,l.material.toneMapped=le.getTransfer(y.colorSpace)!==we,y.matrixAutoUpdate===!0&&y.updateMatrix(),l.material.uniforms.uvTransform.value.copy(y.matrix),(u!==y||d!==y.version||f!==i.toneMapping)&&(l.material.needsUpdate=!0,u=y,d=y.version,f=i.toneMapping),l.layers.enableAll(),P.unshift(l,l.geometry,l.material,0,0,null))}function p(P,w){P.getRGB(Jr,bu(i)),n.buffers.color.setClear(Jr.r,Jr.g,Jr.b,w,a)}return{getClearColor:function(){return o},setClearColor:function(P,w=1){o.set(P),c=w,p(o,c)},getClearAlpha:function(){return c},setClearAlpha:function(P){c=P,p(o,c)},render:_,addToRenderList:m}}function Og(i,t){const e=i.getParameter(i.MAX_VERTEX_ATTRIBS),n={},s=d(null);let r=s,a=!1;function o(b,F,k,H,Z){let tt=!1;const O=u(H,k,F);r!==O&&(r=O,l(r.object)),tt=f(b,H,k,Z),tt&&g(b,H,k,Z),Z!==null&&t.update(Z,i.ELEMENT_ARRAY_BUFFER),(tt||a)&&(a=!1,y(b,F,k,H),Z!==null&&i.bindBuffer(i.ELEMENT_ARRAY_BUFFER,t.get(Z).buffer))}function c(){return i.createVertexArray()}function l(b){return i.bindVertexArray(b)}function h(b){return i.deleteVertexArray(b)}function u(b,F,k){const H=k.wireframe===!0;let Z=n[b.id];Z===void 0&&(Z={},n[b.id]=Z);let tt=Z[F.id];tt===void 0&&(tt={},Z[F.id]=tt);let O=tt[H];return O===void 0&&(O=d(c()),tt[H]=O),O}function d(b){const F=[],k=[],H=[];for(let Z=0;Z<e;Z++)F[Z]=0,k[Z]=0,H[Z]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:F,enabledAttributes:k,attributeDivisors:H,object:b,attributes:{},index:null}}function f(b,F,k,H){const Z=r.attributes,tt=F.attributes;let O=0;const et=k.getAttributes();for(const W in et)if(et[W].location>=0){const pt=Z[W];let mt=tt[W];if(mt===void 0&&(W==="instanceMatrix"&&b.instanceMatrix&&(mt=b.instanceMatrix),W==="instanceColor"&&b.instanceColor&&(mt=b.instanceColor)),pt===void 0||pt.attribute!==mt||mt&&pt.data!==mt.data)return!0;O++}return r.attributesNum!==O||r.index!==H}function g(b,F,k,H){const Z={},tt=F.attributes;let O=0;const et=k.getAttributes();for(const W in et)if(et[W].location>=0){let pt=tt[W];pt===void 0&&(W==="instanceMatrix"&&b.instanceMatrix&&(pt=b.instanceMatrix),W==="instanceColor"&&b.instanceColor&&(pt=b.instanceColor));const mt={};mt.attribute=pt,pt&&pt.data&&(mt.data=pt.data),Z[W]=mt,O++}r.attributes=Z,r.attributesNum=O,r.index=H}function _(){const b=r.newAttributes;for(let F=0,k=b.length;F<k;F++)b[F]=0}function m(b){p(b,0)}function p(b,F){const k=r.newAttributes,H=r.enabledAttributes,Z=r.attributeDivisors;k[b]=1,H[b]===0&&(i.enableVertexAttribArray(b),H[b]=1),Z[b]!==F&&(i.vertexAttribDivisor(b,F),Z[b]=F)}function P(){const b=r.newAttributes,F=r.enabledAttributes;for(let k=0,H=F.length;k<H;k++)F[k]!==b[k]&&(i.disableVertexAttribArray(k),F[k]=0)}function w(b,F,k,H,Z,tt,O){O===!0?i.vertexAttribIPointer(b,F,k,Z,tt):i.vertexAttribPointer(b,F,k,H,Z,tt)}function y(b,F,k,H){_();const Z=H.attributes,tt=k.getAttributes(),O=F.defaultAttributeValues;for(const et in tt){const W=tt[et];if(W.location>=0){let lt=Z[et];if(lt===void 0&&(et==="instanceMatrix"&&b.instanceMatrix&&(lt=b.instanceMatrix),et==="instanceColor"&&b.instanceColor&&(lt=b.instanceColor)),lt!==void 0){const pt=lt.normalized,mt=lt.itemSize,Rt=t.get(lt);if(Rt===void 0)continue;const wt=Rt.buffer,q=Rt.type,J=Rt.bytesPerElement,nt=q===i.INT||q===i.UNSIGNED_INT||lt.gpuType===zc;if(lt.isInterleavedBufferAttribute){const it=lt.data,vt=it.stride,zt=lt.offset;if(it.isInstancedInterleavedBuffer){for(let Qt=0;Qt<W.locationSize;Qt++)p(W.location+Qt,it.meshPerAttribute);b.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=it.meshPerAttribute*it.count)}else for(let Qt=0;Qt<W.locationSize;Qt++)m(W.location+Qt);i.bindBuffer(i.ARRAY_BUFFER,wt);for(let Qt=0;Qt<W.locationSize;Qt++)w(W.location+Qt,mt/W.locationSize,q,pt,vt*J,(zt+mt/W.locationSize*Qt)*J,nt)}else{if(lt.isInstancedBufferAttribute){for(let it=0;it<W.locationSize;it++)p(W.location+it,lt.meshPerAttribute);b.isInstancedMesh!==!0&&H._maxInstanceCount===void 0&&(H._maxInstanceCount=lt.meshPerAttribute*lt.count)}else for(let it=0;it<W.locationSize;it++)m(W.location+it);i.bindBuffer(i.ARRAY_BUFFER,wt);for(let it=0;it<W.locationSize;it++)w(W.location+it,mt/W.locationSize,q,pt,mt*J,mt/W.locationSize*it*J,nt)}}else if(O!==void 0){const pt=O[et];if(pt!==void 0)switch(pt.length){case 2:i.vertexAttrib2fv(W.location,pt);break;case 3:i.vertexAttrib3fv(W.location,pt);break;case 4:i.vertexAttrib4fv(W.location,pt);break;default:i.vertexAttrib1fv(W.location,pt)}}}}P()}function N(){I();for(const b in n){const F=n[b];for(const k in F){const H=F[k];for(const Z in H)h(H[Z].object),delete H[Z];delete F[k]}delete n[b]}}function C(b){if(n[b.id]===void 0)return;const F=n[b.id];for(const k in F){const H=F[k];for(const Z in H)h(H[Z].object),delete H[Z];delete F[k]}delete n[b.id]}function L(b){for(const F in n){const k=n[F];if(k[b.id]===void 0)continue;const H=k[b.id];for(const Z in H)h(H[Z].object),delete H[Z];delete k[b.id]}}function I(){M(),a=!0,r!==s&&(r=s,l(r.object))}function M(){s.geometry=null,s.program=null,s.wireframe=!1}return{setup:o,reset:I,resetDefaultState:M,dispose:N,releaseStatesOfGeometry:C,releaseStatesOfProgram:L,initAttributes:_,enableAttribute:m,disableUnusedAttributes:P}}function kg(i,t,e){let n;function s(l){n=l}function r(l,h){i.drawArrays(n,l,h),e.update(h,n,1)}function a(l,h,u){u!==0&&(i.drawArraysInstanced(n,l,h,u),e.update(h,n,u))}function o(l,h,u){if(u===0)return;t.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n,l,0,h,0,u);let f=0;for(let g=0;g<u;g++)f+=h[g];e.update(f,n,1)}function c(l,h,u,d){if(u===0)return;const f=t.get("WEBGL_multi_draw");if(f===null)for(let g=0;g<l.length;g++)a(l[g],h[g],d[g]);else{f.multiDrawArraysInstancedWEBGL(n,l,0,h,0,d,0,u);let g=0;for(let _=0;_<u;_++)g+=h[_]*d[_];e.update(g,n,1)}}this.setMode=s,this.render=r,this.renderInstances=a,this.renderMultiDraw=o,this.renderMultiDrawInstances=c}function Bg(i,t,e,n){let s;function r(){if(s!==void 0)return s;if(t.has("EXT_texture_filter_anisotropic")===!0){const L=t.get("EXT_texture_filter_anisotropic");s=i.getParameter(L.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else s=0;return s}function a(L){return!(L!==Pn&&n.convert(L)!==i.getParameter(i.IMPLEMENTATION_COLOR_READ_FORMAT))}function o(L){const I=L===br&&(t.has("EXT_color_buffer_half_float")||t.has("EXT_color_buffer_float"));return!(L!==fi&&n.convert(L)!==i.getParameter(i.IMPLEMENTATION_COLOR_READ_TYPE)&&L!==qn&&!I)}function c(L){if(L==="highp"){if(i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.HIGH_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.HIGH_FLOAT).precision>0)return"highp";L="mediump"}return L==="mediump"&&i.getShaderPrecisionFormat(i.VERTEX_SHADER,i.MEDIUM_FLOAT).precision>0&&i.getShaderPrecisionFormat(i.FRAGMENT_SHADER,i.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let l=e.precision!==void 0?e.precision:"highp";const h=c(l);h!==l&&(console.warn("THREE.WebGLRenderer:",l,"not supported, using",h,"instead."),l=h);const u=e.logarithmicDepthBuffer===!0,d=e.reverseDepthBuffer===!0&&t.has("EXT_clip_control"),f=i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS),g=i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS),_=i.getParameter(i.MAX_TEXTURE_SIZE),m=i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE),p=i.getParameter(i.MAX_VERTEX_ATTRIBS),P=i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS),w=i.getParameter(i.MAX_VARYING_VECTORS),y=i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS),N=g>0,C=i.getParameter(i.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:c,textureFormatReadable:a,textureTypeReadable:o,precision:l,logarithmicDepthBuffer:u,reverseDepthBuffer:d,maxTextures:f,maxVertexTextures:g,maxTextureSize:_,maxCubemapSize:m,maxAttributes:p,maxVertexUniforms:P,maxVaryings:w,maxFragmentUniforms:y,vertexTextures:N,maxSamples:C}}function zg(i){const t=this;let e=null,n=0,s=!1,r=!1;const a=new ci,o=new re,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(u,d){const f=u.length!==0||d||n!==0||s;return s=d,n=u.length,f},this.beginShadows=function(){r=!0,h(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(u,d){e=h(u,d,0)},this.setState=function(u,d,f){const g=u.clippingPlanes,_=u.clipIntersection,m=u.clipShadows,p=i.get(u);if(!s||g===null||g.length===0||r&&!m)r?h(null):l();else{const P=r?0:n,w=P*4;let y=p.clippingState||null;c.value=y,y=h(g,d,w,f);for(let N=0;N!==w;++N)y[N]=e[N];p.clippingState=y,this.numIntersection=_?this.numPlanes:0,this.numPlanes+=P}};function l(){c.value!==e&&(c.value=e,c.needsUpdate=n>0),t.numPlanes=n,t.numIntersection=0}function h(u,d,f,g){const _=u!==null?u.length:0;let m=null;if(_!==0){if(m=c.value,g!==!0||m===null){const p=f+_*4,P=d.matrixWorldInverse;o.getNormalMatrix(P),(m===null||m.length<p)&&(m=new Float32Array(p));for(let w=0,y=f;w!==_;++w,y+=4)a.copy(u[w]).applyMatrix4(P,o),a.normal.toArray(m,y),m[y+3]=a.constant}c.value=m,c.needsUpdate=!0}return t.numPlanes=_,t.numIntersection=0,m}}function Vg(i){let t=new WeakMap;function e(a,o){return o===ic?a.mapping=Ps:o===sc&&(a.mapping=Ls),a}function n(a){if(a&&a.isTexture){const o=a.mapping;if(o===ic||o===sc)if(t.has(a)){const c=t.get(a).texture;return e(c,a.mapping)}else{const c=a.image;if(c&&c.height>0){const l=new Zf(c.height);return l.fromEquirectangularTexture(i,a),t.set(a,l),a.addEventListener("dispose",s),e(l.texture,a.mapping)}else return null}}return a}function s(a){const o=a.target;o.removeEventListener("dispose",s);const c=t.get(o);c!==void 0&&(t.delete(o),c.dispose())}function r(){t=new WeakMap}return{get:n,dispose:r}}class $c extends Su{constructor(t=-1,e=1,n=1,s=-1,r=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=t,this.right=e,this.top=n,this.bottom=s,this.near=r,this.far=a,this.updateProjectionMatrix()}copy(t,e){return super.copy(t,e),this.left=t.left,this.right=t.right,this.top=t.top,this.bottom=t.bottom,this.near=t.near,this.far=t.far,this.zoom=t.zoom,this.view=t.view===null?null:Object.assign({},t.view),this}setViewOffset(t,e,n,s,r,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=t,this.view.fullHeight=e,this.view.offsetX=n,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){const t=(this.right-this.left)/(2*this.zoom),e=(this.top-this.bottom)/(2*this.zoom),n=(this.right+this.left)/2,s=(this.top+this.bottom)/2;let r=n-t,a=n+t,o=s+e,c=s-e;if(this.view!==null&&this.view.enabled){const l=(this.right-this.left)/this.view.fullWidth/this.zoom,h=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=l*this.view.offsetX,a=r+l*this.view.width,o-=h*this.view.offsetY,c=o-h*this.view.height}this.projectionMatrix.makeOrthographic(r,a,o,c,this.near,this.far,this.coordinateSystem),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(t){const e=super.toJSON(t);return e.object.zoom=this.zoom,e.object.left=this.left,e.object.right=this.right,e.object.top=this.top,e.object.bottom=this.bottom,e.object.near=this.near,e.object.far=this.far,this.view!==null&&(e.object.view=Object.assign({},this.view)),e}}const Ms=4,ql=[.125,.215,.35,.446,.526,.582],ji=20,wo=new $c,jl=new Jt;let To=null,Ao=0,Co=0,Ro=!1;const Xi=(1+Math.sqrt(5))/2,vs=1/Xi,Yl=[new D(-Xi,vs,0),new D(Xi,vs,0),new D(-vs,0,Xi),new D(vs,0,Xi),new D(0,Xi,-vs),new D(0,Xi,vs),new D(-1,1,-1),new D(1,1,-1),new D(-1,1,1),new D(1,1,1)];class $l{constructor(t){this._renderer=t,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(t,e=0,n=.1,s=100){To=this._renderer.getRenderTarget(),Ao=this._renderer.getActiveCubeFace(),Co=this._renderer.getActiveMipmapLevel(),Ro=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(256);const r=this._allocateTargets();return r.depthBuffer=!0,this._sceneToCubeUV(t,n,s,r),e>0&&this._blur(r,0,0,e),this._applyPMREM(r),this._cleanup(r),r}fromEquirectangular(t,e=null){return this._fromTexture(t,e)}fromCubemap(t,e=null){return this._fromTexture(t,e)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Zl(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=Jl(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(t){this._lodMax=Math.floor(Math.log2(t)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let t=0;t<this._lodPlanes.length;t++)this._lodPlanes[t].dispose()}_cleanup(t){this._renderer.setRenderTarget(To,Ao,Co),this._renderer.xr.enabled=Ro,t.scissorTest=!1,Zr(t,0,0,t.width,t.height)}_fromTexture(t,e){t.mapping===Ps||t.mapping===Ls?this._setSize(t.image.length===0?16:t.image[0].width||t.image[0].image.width):this._setSize(t.image.width/4),To=this._renderer.getRenderTarget(),Ao=this._renderer.getActiveCubeFace(),Co=this._renderer.getActiveMipmapLevel(),Ro=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;const n=e||this._allocateTargets();return this._textureToCubeUV(t,n),this._applyPMREM(n),this._cleanup(n),n}_allocateTargets(){const t=3*Math.max(this._cubeSize,112),e=4*this._cubeSize,n={magFilter:xn,minFilter:xn,generateMipmaps:!1,type:br,format:Pn,colorSpace:Hs,depthBuffer:!1},s=Kl(t,e,n);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==t||this._pingPongRenderTarget.height!==e){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Kl(t,e,n);const{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=Hg(r)),this._blurMaterial=Gg(r,t,e)}return s}_compileMaterial(t){const e=new ge(this._lodPlanes[0],t);this._renderer.compile(e,wo)}_sceneToCubeUV(t,e,n,s){const o=new tn(90,1,e,n),c=[1,-1,1,1,1,1],l=[1,1,1,-1,-1,-1],h=this._renderer,u=h.autoClear,d=h.toneMapping;h.getClearColor(jl),h.toneMapping=Li,h.autoClear=!1;const f=new Ke({name:"PMREM.Background",side:fn,depthWrite:!1,depthTest:!1}),g=new ge(new Ws,f);let _=!1;const m=t.background;m?m.isColor&&(f.color.copy(m),t.background=null,_=!0):(f.color.copy(jl),_=!0);for(let p=0;p<6;p++){const P=p%3;P===0?(o.up.set(0,c[p],0),o.lookAt(l[p],0,0)):P===1?(o.up.set(0,0,c[p]),o.lookAt(0,l[p],0)):(o.up.set(0,c[p],0),o.lookAt(0,0,l[p]));const w=this._cubeSize;Zr(s,P*w,p>2?w:0,w,w),h.setRenderTarget(s),_&&h.render(g,o),h.render(t,o)}g.geometry.dispose(),g.material.dispose(),h.toneMapping=d,h.autoClear=u,t.background=m}_textureToCubeUV(t,e){const n=this._renderer,s=t.mapping===Ps||t.mapping===Ls;s?(this._cubemapMaterial===null&&(this._cubemapMaterial=Zl()),this._cubemapMaterial.uniforms.flipEnvMap.value=t.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=Jl());const r=s?this._cubemapMaterial:this._equirectMaterial,a=new ge(this._lodPlanes[0],r),o=r.uniforms;o.envMap.value=t;const c=this._cubeSize;Zr(e,0,0,3*c,2*c),n.setRenderTarget(e),n.render(a,wo)}_applyPMREM(t){const e=this._renderer,n=e.autoClear;e.autoClear=!1;const s=this._lodPlanes.length;for(let r=1;r<s;r++){const a=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),o=Yl[(s-r-1)%Yl.length];this._blur(t,r-1,r,a,o)}e.autoClear=n}_blur(t,e,n,s,r){const a=this._pingPongRenderTarget;this._halfBlur(t,a,e,n,s,"latitudinal",r),this._halfBlur(a,t,n,n,s,"longitudinal",r)}_halfBlur(t,e,n,s,r,a,o){const c=this._renderer,l=this._blurMaterial;a!=="latitudinal"&&a!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");const h=3,u=new ge(this._lodPlanes[s],l),d=l.uniforms,f=this._sizeLods[n]-1,g=isFinite(r)?Math.PI/(2*f):2*Math.PI/(2*ji-1),_=r/g,m=isFinite(r)?1+Math.floor(h*_):ji;m>ji&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${ji}`);const p=[];let P=0;for(let L=0;L<ji;++L){const I=L/_,M=Math.exp(-I*I/2);p.push(M),L===0?P+=M:L<m&&(P+=2*M)}for(let L=0;L<p.length;L++)p[L]=p[L]/P;d.envMap.value=t.texture,d.samples.value=m,d.weights.value=p,d.latitudinal.value=a==="latitudinal",o&&(d.poleAxis.value=o);const{_lodMax:w}=this;d.dTheta.value=g,d.mipInt.value=w-n;const y=this._sizeLods[s],N=3*y*(s>w-Ms?s-w+Ms:0),C=4*(this._cubeSize-y);Zr(e,N,C,3*y,2*y),c.setRenderTarget(e),c.render(u,wo)}}function Hg(i){const t=[],e=[],n=[];let s=i;const r=i-Ms+1+ql.length;for(let a=0;a<r;a++){const o=Math.pow(2,s);e.push(o);let c=1/o;a>i-Ms?c=ql[a-i+Ms-1]:a===0&&(c=0),n.push(c);const l=1/(o-2),h=-l,u=1+l,d=[h,h,u,h,u,u,h,h,u,u,h,u],f=6,g=6,_=3,m=2,p=1,P=new Float32Array(_*g*f),w=new Float32Array(m*g*f),y=new Float32Array(p*g*f);for(let C=0;C<f;C++){const L=C%3*2/3-1,I=C>2?0:-1,M=[L,I,0,L+2/3,I,0,L+2/3,I+1,0,L,I,0,L+2/3,I+1,0,L,I+1,0];P.set(M,_*g*C),w.set(d,m*g*C);const b=[C,C,C,C,C,C];y.set(b,p*g*C)}const N=new Le;N.setAttribute("position",new bn(P,_)),N.setAttribute("uv",new bn(w,m)),N.setAttribute("faceIndex",new bn(y,p)),t.push(N),s>Ms&&s--}return{lodPlanes:t,sizeLods:e,sigmas:n}}function Kl(i,t,e){const n=new Ji(i,t,e);return n.texture.mapping=Ba,n.texture.name="PMREM.cubeUv",n.scissorTest=!0,n}function Zr(i,t,e,n,s){i.viewport.set(t,e,n,s),i.scissor.set(t,e,n,s)}function Gg(i,t,e){const n=new Float32Array(ji),s=new D(0,1,0);return new Ni({name:"SphericalGaussianBlur",defines:{n:ji,CUBEUV_TEXEL_WIDTH:1/t,CUBEUV_TEXEL_HEIGHT:1/e,CUBEUV_MAX_MIP:`${i}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:n},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:s}},vertexShader:Kc(),fragmentShader:`

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
		`,blending:Pi,depthTest:!1,depthWrite:!1})}function Jl(){return new Ni({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Kc(),fragmentShader:`

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
		`,blending:Pi,depthTest:!1,depthWrite:!1})}function Zl(){return new Ni({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Kc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:Pi,depthTest:!1,depthWrite:!1})}function Kc(){return`

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
	`}function Wg(i){let t=new WeakMap,e=null;function n(o){if(o&&o.isTexture){const c=o.mapping,l=c===ic||c===sc,h=c===Ps||c===Ls;if(l||h){let u=t.get(o);const d=u!==void 0?u.texture.pmremVersion:0;if(o.isRenderTargetTexture&&o.pmremVersion!==d)return e===null&&(e=new $l(i)),u=l?e.fromEquirectangular(o,u):e.fromCubemap(o,u),u.texture.pmremVersion=o.pmremVersion,t.set(o,u),u.texture;if(u!==void 0)return u.texture;{const f=o.image;return l&&f&&f.height>0||h&&f&&s(f)?(e===null&&(e=new $l(i)),u=l?e.fromEquirectangular(o):e.fromCubemap(o),u.texture.pmremVersion=o.pmremVersion,t.set(o,u),o.addEventListener("dispose",r),u.texture):null}}}return o}function s(o){let c=0;const l=6;for(let h=0;h<l;h++)o[h]!==void 0&&c++;return c===l}function r(o){const c=o.target;c.removeEventListener("dispose",r);const l=t.get(c);l!==void 0&&(t.delete(c),l.dispose())}function a(){t=new WeakMap,e!==null&&(e.dispose(),e=null)}return{get:n,dispose:a}}function Xg(i){const t={};function e(n){if(t[n]!==void 0)return t[n];let s;switch(n){case"WEBGL_depth_texture":s=i.getExtension("WEBGL_depth_texture")||i.getExtension("MOZ_WEBGL_depth_texture")||i.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":s=i.getExtension("EXT_texture_filter_anisotropic")||i.getExtension("MOZ_EXT_texture_filter_anisotropic")||i.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":s=i.getExtension("WEBGL_compressed_texture_s3tc")||i.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":s=i.getExtension("WEBGL_compressed_texture_pvrtc")||i.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:s=i.getExtension(n)}return t[n]=s,s}return{has:function(n){return e(n)!==null},init:function(){e("EXT_color_buffer_float"),e("WEBGL_clip_cull_distance"),e("OES_texture_float_linear"),e("EXT_color_buffer_half_float"),e("WEBGL_multisampled_render_to_texture"),e("WEBGL_render_shared_exponent")},get:function(n){const s=e(n);return s===null&&rr("THREE.WebGLRenderer: "+n+" extension not supported."),s}}}function qg(i,t,e,n){const s={},r=new WeakMap;function a(u){const d=u.target;d.index!==null&&t.remove(d.index);for(const g in d.attributes)t.remove(d.attributes[g]);for(const g in d.morphAttributes){const _=d.morphAttributes[g];for(let m=0,p=_.length;m<p;m++)t.remove(_[m])}d.removeEventListener("dispose",a),delete s[d.id];const f=r.get(d);f&&(t.remove(f),r.delete(d)),n.releaseStatesOfGeometry(d),d.isInstancedBufferGeometry===!0&&delete d._maxInstanceCount,e.memory.geometries--}function o(u,d){return s[d.id]===!0||(d.addEventListener("dispose",a),s[d.id]=!0,e.memory.geometries++),d}function c(u){const d=u.attributes;for(const g in d)t.update(d[g],i.ARRAY_BUFFER);const f=u.morphAttributes;for(const g in f){const _=f[g];for(let m=0,p=_.length;m<p;m++)t.update(_[m],i.ARRAY_BUFFER)}}function l(u){const d=[],f=u.index,g=u.attributes.position;let _=0;if(f!==null){const P=f.array;_=f.version;for(let w=0,y=P.length;w<y;w+=3){const N=P[w+0],C=P[w+1],L=P[w+2];d.push(N,C,C,L,L,N)}}else if(g!==void 0){const P=g.array;_=g.version;for(let w=0,y=P.length/3-1;w<y;w+=3){const N=w+0,C=w+1,L=w+2;d.push(N,C,C,L,L,N)}}else return;const m=new(gu(d)?Mu:yu)(d,1);m.version=_;const p=r.get(u);p&&t.remove(p),r.set(u,m)}function h(u){const d=r.get(u);if(d){const f=u.index;f!==null&&d.version<f.version&&l(u)}else l(u);return r.get(u)}return{get:o,update:c,getWireframeAttribute:h}}function jg(i,t,e){let n;function s(d){n=d}let r,a;function o(d){r=d.type,a=d.bytesPerElement}function c(d,f){i.drawElements(n,f,r,d*a),e.update(f,n,1)}function l(d,f,g){g!==0&&(i.drawElementsInstanced(n,f,r,d*a,g),e.update(f,n,g))}function h(d,f,g){if(g===0)return;t.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n,f,0,r,d,0,g);let m=0;for(let p=0;p<g;p++)m+=f[p];e.update(m,n,1)}function u(d,f,g,_){if(g===0)return;const m=t.get("WEBGL_multi_draw");if(m===null)for(let p=0;p<d.length;p++)l(d[p]/a,f[p],_[p]);else{m.multiDrawElementsInstancedWEBGL(n,f,0,r,d,0,_,0,g);let p=0;for(let P=0;P<g;P++)p+=f[P]*_[P];e.update(p,n,1)}}this.setMode=s,this.setIndex=o,this.render=c,this.renderInstances=l,this.renderMultiDraw=h,this.renderMultiDrawInstances=u}function Yg(i){const t={geometries:0,textures:0},e={frame:0,calls:0,triangles:0,points:0,lines:0};function n(r,a,o){switch(e.calls++,a){case i.TRIANGLES:e.triangles+=o*(r/3);break;case i.LINES:e.lines+=o*(r/2);break;case i.LINE_STRIP:e.lines+=o*(r-1);break;case i.LINE_LOOP:e.lines+=o*r;break;case i.POINTS:e.points+=o*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",a);break}}function s(){e.calls=0,e.triangles=0,e.points=0,e.lines=0}return{memory:t,render:e,programs:null,autoReset:!0,reset:s,update:n}}function $g(i,t,e){const n=new WeakMap,s=new ye;function r(a,o,c){const l=a.morphTargetInfluences,h=o.morphAttributes.position||o.morphAttributes.normal||o.morphAttributes.color,u=h!==void 0?h.length:0;let d=n.get(o);if(d===void 0||d.count!==u){let b=function(){I.dispose(),n.delete(o),o.removeEventListener("dispose",b)};var f=b;d!==void 0&&d.texture.dispose();const g=o.morphAttributes.position!==void 0,_=o.morphAttributes.normal!==void 0,m=o.morphAttributes.color!==void 0,p=o.morphAttributes.position||[],P=o.morphAttributes.normal||[],w=o.morphAttributes.color||[];let y=0;g===!0&&(y=1),_===!0&&(y=2),m===!0&&(y=3);let N=o.attributes.position.count*y,C=1;N>t.maxTextureSize&&(C=Math.ceil(N/t.maxTextureSize),N=t.maxTextureSize);const L=new Float32Array(N*C*4*u),I=new vu(L,N,C,u);I.type=qn,I.needsUpdate=!0;const M=y*4;for(let F=0;F<u;F++){const k=p[F],H=P[F],Z=w[F],tt=N*C*4*F;for(let O=0;O<k.count;O++){const et=O*M;g===!0&&(s.fromBufferAttribute(k,O),L[tt+et+0]=s.x,L[tt+et+1]=s.y,L[tt+et+2]=s.z,L[tt+et+3]=0),_===!0&&(s.fromBufferAttribute(H,O),L[tt+et+4]=s.x,L[tt+et+5]=s.y,L[tt+et+6]=s.z,L[tt+et+7]=0),m===!0&&(s.fromBufferAttribute(Z,O),L[tt+et+8]=s.x,L[tt+et+9]=s.y,L[tt+et+10]=s.z,L[tt+et+11]=Z.itemSize===4?s.w:1)}}d={count:u,texture:I,size:new At(N,C)},n.set(o,d),o.addEventListener("dispose",b)}if(a.isInstancedMesh===!0&&a.morphTexture!==null)c.getUniforms().setValue(i,"morphTexture",a.morphTexture,e);else{let g=0;for(let m=0;m<l.length;m++)g+=l[m];const _=o.morphTargetsRelative?1:1-g;c.getUniforms().setValue(i,"morphTargetBaseInfluence",_),c.getUniforms().setValue(i,"morphTargetInfluences",l)}c.getUniforms().setValue(i,"morphTargetsTexture",d.texture,e),c.getUniforms().setValue(i,"morphTargetsTextureSize",d.size)}return{update:r}}function Kg(i,t,e,n){let s=new WeakMap;function r(c){const l=n.render.frame,h=c.geometry,u=t.get(c,h);if(s.get(u)!==l&&(t.update(u),s.set(u,l)),c.isInstancedMesh&&(c.hasEventListener("dispose",o)===!1&&c.addEventListener("dispose",o),s.get(c)!==l&&(e.update(c.instanceMatrix,i.ARRAY_BUFFER),c.instanceColor!==null&&e.update(c.instanceColor,i.ARRAY_BUFFER),s.set(c,l))),c.isSkinnedMesh){const d=c.skeleton;s.get(d)!==l&&(d.update(),s.set(d,l))}return u}function a(){s=new WeakMap}function o(c){const l=c.target;l.removeEventListener("dispose",o),e.remove(l.instanceMatrix),l.instanceColor!==null&&e.remove(l.instanceColor)}return{update:r,dispose:a}}class Tu extends Je{constructor(t,e,n,s,r,a,o,c,l,h=Es){if(h!==Es&&h!==Ds)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");n===void 0&&h===Es&&(n=Ki),n===void 0&&h===Ds&&(n=Ns),super(null,s,r,a,o,c,h,n,l),this.isDepthTexture=!0,this.image={width:t,height:e},this.magFilter=o!==void 0?o:Mn,this.minFilter=c!==void 0?c:Mn,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(t){return super.copy(t),this.compareFunction=t.compareFunction,this}toJSON(t){const e=super.toJSON(t);return this.compareFunction!==null&&(e.compareFunction=this.compareFunction),e}}const Au=new Je,Ql=new Tu(1,1),Cu=new vu,Ru=new Ff,Pu=new Eu,th=[],eh=[],nh=new Float32Array(16),ih=new Float32Array(9),sh=new Float32Array(4);function Xs(i,t,e){const n=i[0];if(n<=0||n>0)return i;const s=t*e;let r=th[s];if(r===void 0&&(r=new Float32Array(s),th[s]=r),t!==0){n.toArray(r,0);for(let a=1,o=0;a!==t;++a)o+=e,i[a].toArray(r,o)}return r}function We(i,t){if(i.length!==t.length)return!1;for(let e=0,n=i.length;e<n;e++)if(i[e]!==t[e])return!1;return!0}function Xe(i,t){for(let e=0,n=t.length;e<n;e++)i[e]=t[e]}function Ga(i,t){let e=eh[t];e===void 0&&(e=new Int32Array(t),eh[t]=e);for(let n=0;n!==t;++n)e[n]=i.allocateTextureUnit();return e}function Jg(i,t){const e=this.cache;e[0]!==t&&(i.uniform1f(this.addr,t),e[0]=t)}function Zg(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2f(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(We(e,t))return;i.uniform2fv(this.addr,t),Xe(e,t)}}function Qg(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3f(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else if(t.r!==void 0)(e[0]!==t.r||e[1]!==t.g||e[2]!==t.b)&&(i.uniform3f(this.addr,t.r,t.g,t.b),e[0]=t.r,e[1]=t.g,e[2]=t.b);else{if(We(e,t))return;i.uniform3fv(this.addr,t),Xe(e,t)}}function t_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4f(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(We(e,t))return;i.uniform4fv(this.addr,t),Xe(e,t)}}function e_(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(We(e,t))return;i.uniformMatrix2fv(this.addr,!1,t),Xe(e,t)}else{if(We(e,n))return;sh.set(n),i.uniformMatrix2fv(this.addr,!1,sh),Xe(e,n)}}function n_(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(We(e,t))return;i.uniformMatrix3fv(this.addr,!1,t),Xe(e,t)}else{if(We(e,n))return;ih.set(n),i.uniformMatrix3fv(this.addr,!1,ih),Xe(e,n)}}function i_(i,t){const e=this.cache,n=t.elements;if(n===void 0){if(We(e,t))return;i.uniformMatrix4fv(this.addr,!1,t),Xe(e,t)}else{if(We(e,n))return;nh.set(n),i.uniformMatrix4fv(this.addr,!1,nh),Xe(e,n)}}function s_(i,t){const e=this.cache;e[0]!==t&&(i.uniform1i(this.addr,t),e[0]=t)}function r_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2i(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(We(e,t))return;i.uniform2iv(this.addr,t),Xe(e,t)}}function a_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3i(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(We(e,t))return;i.uniform3iv(this.addr,t),Xe(e,t)}}function o_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4i(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(We(e,t))return;i.uniform4iv(this.addr,t),Xe(e,t)}}function c_(i,t){const e=this.cache;e[0]!==t&&(i.uniform1ui(this.addr,t),e[0]=t)}function l_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y)&&(i.uniform2ui(this.addr,t.x,t.y),e[0]=t.x,e[1]=t.y);else{if(We(e,t))return;i.uniform2uiv(this.addr,t),Xe(e,t)}}function h_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z)&&(i.uniform3ui(this.addr,t.x,t.y,t.z),e[0]=t.x,e[1]=t.y,e[2]=t.z);else{if(We(e,t))return;i.uniform3uiv(this.addr,t),Xe(e,t)}}function u_(i,t){const e=this.cache;if(t.x!==void 0)(e[0]!==t.x||e[1]!==t.y||e[2]!==t.z||e[3]!==t.w)&&(i.uniform4ui(this.addr,t.x,t.y,t.z,t.w),e[0]=t.x,e[1]=t.y,e[2]=t.z,e[3]=t.w);else{if(We(e,t))return;i.uniform4uiv(this.addr,t),Xe(e,t)}}function d_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s);let r;this.type===i.SAMPLER_2D_SHADOW?(Ql.compareFunction=mu,r=Ql):r=Au,e.setTexture2D(t||r,s)}function f_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTexture3D(t||Ru,s)}function p_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTextureCube(t||Pu,s)}function m_(i,t,e){const n=this.cache,s=e.allocateTextureUnit();n[0]!==s&&(i.uniform1i(this.addr,s),n[0]=s),e.setTexture2DArray(t||Cu,s)}function g_(i){switch(i){case 5126:return Jg;case 35664:return Zg;case 35665:return Qg;case 35666:return t_;case 35674:return e_;case 35675:return n_;case 35676:return i_;case 5124:case 35670:return s_;case 35667:case 35671:return r_;case 35668:case 35672:return a_;case 35669:case 35673:return o_;case 5125:return c_;case 36294:return l_;case 36295:return h_;case 36296:return u_;case 35678:case 36198:case 36298:case 36306:case 35682:return d_;case 35679:case 36299:case 36307:return f_;case 35680:case 36300:case 36308:case 36293:return p_;case 36289:case 36303:case 36311:case 36292:return m_}}function __(i,t){i.uniform1fv(this.addr,t)}function v_(i,t){const e=Xs(t,this.size,2);i.uniform2fv(this.addr,e)}function x_(i,t){const e=Xs(t,this.size,3);i.uniform3fv(this.addr,e)}function y_(i,t){const e=Xs(t,this.size,4);i.uniform4fv(this.addr,e)}function M_(i,t){const e=Xs(t,this.size,4);i.uniformMatrix2fv(this.addr,!1,e)}function b_(i,t){const e=Xs(t,this.size,9);i.uniformMatrix3fv(this.addr,!1,e)}function S_(i,t){const e=Xs(t,this.size,16);i.uniformMatrix4fv(this.addr,!1,e)}function E_(i,t){i.uniform1iv(this.addr,t)}function w_(i,t){i.uniform2iv(this.addr,t)}function T_(i,t){i.uniform3iv(this.addr,t)}function A_(i,t){i.uniform4iv(this.addr,t)}function C_(i,t){i.uniform1uiv(this.addr,t)}function R_(i,t){i.uniform2uiv(this.addr,t)}function P_(i,t){i.uniform3uiv(this.addr,t)}function L_(i,t){i.uniform4uiv(this.addr,t)}function N_(i,t,e){const n=this.cache,s=t.length,r=Ga(e,s);We(n,r)||(i.uniform1iv(this.addr,r),Xe(n,r));for(let a=0;a!==s;++a)e.setTexture2D(t[a]||Au,r[a])}function D_(i,t,e){const n=this.cache,s=t.length,r=Ga(e,s);We(n,r)||(i.uniform1iv(this.addr,r),Xe(n,r));for(let a=0;a!==s;++a)e.setTexture3D(t[a]||Ru,r[a])}function I_(i,t,e){const n=this.cache,s=t.length,r=Ga(e,s);We(n,r)||(i.uniform1iv(this.addr,r),Xe(n,r));for(let a=0;a!==s;++a)e.setTextureCube(t[a]||Pu,r[a])}function U_(i,t,e){const n=this.cache,s=t.length,r=Ga(e,s);We(n,r)||(i.uniform1iv(this.addr,r),Xe(n,r));for(let a=0;a!==s;++a)e.setTexture2DArray(t[a]||Cu,r[a])}function F_(i){switch(i){case 5126:return __;case 35664:return v_;case 35665:return x_;case 35666:return y_;case 35674:return M_;case 35675:return b_;case 35676:return S_;case 5124:case 35670:return E_;case 35667:case 35671:return w_;case 35668:case 35672:return T_;case 35669:case 35673:return A_;case 5125:return C_;case 36294:return R_;case 36295:return P_;case 36296:return L_;case 35678:case 36198:case 36298:case 36306:case 35682:return N_;case 35679:case 36299:case 36307:return D_;case 35680:case 36300:case 36308:case 36293:return I_;case 36289:case 36303:case 36311:case 36292:return U_}}class O_{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.setValue=g_(e.type)}}class k_{constructor(t,e,n){this.id=t,this.addr=n,this.cache=[],this.type=e.type,this.size=e.size,this.setValue=F_(e.type)}}class B_{constructor(t){this.id=t,this.seq=[],this.map={}}setValue(t,e,n){const s=this.seq;for(let r=0,a=s.length;r!==a;++r){const o=s[r];o.setValue(t,e[o.id],n)}}}const Po=/(\w+)(\])?(\[|\.)?/g;function rh(i,t){i.seq.push(t),i.map[t.id]=t}function z_(i,t,e){const n=i.name,s=n.length;for(Po.lastIndex=0;;){const r=Po.exec(n),a=Po.lastIndex;let o=r[1];const c=r[2]==="]",l=r[3];if(c&&(o=o|0),l===void 0||l==="["&&a+2===s){rh(e,l===void 0?new O_(o,i,t):new k_(o,i,t));break}else{let u=e.map[o];u===void 0&&(u=new B_(o),rh(e,u)),e=u}}}class xa{constructor(t,e){this.seq=[],this.map={};const n=t.getProgramParameter(e,t.ACTIVE_UNIFORMS);for(let s=0;s<n;++s){const r=t.getActiveUniform(e,s),a=t.getUniformLocation(e,r.name);z_(r,a,this)}}setValue(t,e,n,s){const r=this.map[e];r!==void 0&&r.setValue(t,n,s)}setOptional(t,e,n){const s=e[n];s!==void 0&&this.setValue(t,n,s)}static upload(t,e,n,s){for(let r=0,a=e.length;r!==a;++r){const o=e[r],c=n[o.id];c.needsUpdate!==!1&&o.setValue(t,c.value,s)}}static seqWithValue(t,e){const n=[];for(let s=0,r=t.length;s!==r;++s){const a=t[s];a.id in e&&n.push(a)}return n}}function ah(i,t,e){const n=i.createShader(t);return i.shaderSource(n,e),i.compileShader(n),n}const V_=37297;let H_=0;function G_(i,t){const e=i.split(`
`),n=[],s=Math.max(t-6,0),r=Math.min(t+6,e.length);for(let a=s;a<r;a++){const o=a+1;n.push(`${o===t?">":" "} ${o}: ${e[a]}`)}return n.join(`
`)}const oh=new re;function W_(i){le._getMatrix(oh,le.workingColorSpace,i);const t=`mat3( ${oh.elements.map(e=>e.toFixed(4))} )`;switch(le.getTransfer(i)){case Va:return[t,"LinearTransferOETF"];case we:return[t,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",i),[t,"LinearTransferOETF"]}}function ch(i,t,e){const n=i.getShaderParameter(t,i.COMPILE_STATUS),s=i.getShaderInfoLog(t).trim();if(n&&s==="")return"";const r=/ERROR: 0:(\d+)/.exec(s);if(r){const a=parseInt(r[1]);return e.toUpperCase()+`

`+s+`

`+G_(i.getShaderSource(t),a)}else return s}function X_(i,t){const e=W_(t);return[`vec4 ${i}( vec4 value ) {`,`	return ${e[1]}( vec4( value.rgb * ${e[0]}, value.a ) );`,"}"].join(`
`)}function q_(i,t){let e;switch(t){case qd:e="Linear";break;case jd:e="Reinhard";break;case Yd:e="Cineon";break;case iu:e="ACESFilmic";break;case Kd:e="AgX";break;case Jd:e="Neutral";break;case $d:e="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",t),e="Linear"}return"vec3 "+i+"( vec3 color ) { return "+e+"ToneMapping( color ); }"}const Qr=new D;function j_(){le.getLuminanceCoefficients(Qr);const i=Qr.x.toFixed(4),t=Qr.y.toFixed(4),e=Qr.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${i}, ${t}, ${e} );`,"	return dot( weights, rgb );","}"].join(`
`)}function Y_(i){return[i.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",i.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(ar).join(`
`)}function $_(i){const t=[];for(const e in i){const n=i[e];n!==!1&&t.push("#define "+e+" "+n)}return t.join(`
`)}function K_(i,t){const e={},n=i.getProgramParameter(t,i.ACTIVE_ATTRIBUTES);for(let s=0;s<n;s++){const r=i.getActiveAttrib(t,s),a=r.name;let o=1;r.type===i.FLOAT_MAT2&&(o=2),r.type===i.FLOAT_MAT3&&(o=3),r.type===i.FLOAT_MAT4&&(o=4),e[a]={type:r.type,location:i.getAttribLocation(t,a),locationSize:o}}return e}function ar(i){return i!==""}function lh(i,t){const e=t.numSpotLightShadows+t.numSpotLightMaps-t.numSpotLightShadowsWithMaps;return i.replace(/NUM_DIR_LIGHTS/g,t.numDirLights).replace(/NUM_SPOT_LIGHTS/g,t.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,t.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,e).replace(/NUM_RECT_AREA_LIGHTS/g,t.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,t.numPointLights).replace(/NUM_HEMI_LIGHTS/g,t.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,t.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,t.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,t.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,t.numPointLightShadows)}function hh(i,t){return i.replace(/NUM_CLIPPING_PLANES/g,t.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,t.numClippingPlanes-t.numClipIntersection)}const J_=/^[ \t]*#include +<([\w\d./]+)>/gm;function Dc(i){return i.replace(J_,Q_)}const Z_=new Map;function Q_(i,t){let e=ae[t];if(e===void 0){const n=Z_.get(t);if(n!==void 0)e=ae[n],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',t,n);else throw new Error("Can not resolve #include <"+t+">")}return Dc(e)}const t0=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function uh(i){return i.replace(t0,e0)}function e0(i,t,e,n){let s="";for(let r=parseInt(t);r<parseInt(e);r++)s+=n.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return s}function dh(i){let t=`precision ${i.precision} float;
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
#define LOW_PRECISION`),t}function n0(i){let t="SHADOWMAP_TYPE_BASIC";return i.shadowMapType===nu?t="SHADOWMAP_TYPE_PCF":i.shadowMapType===wd?t="SHADOWMAP_TYPE_PCF_SOFT":i.shadowMapType===oi&&(t="SHADOWMAP_TYPE_VSM"),t}function i0(i){let t="ENVMAP_TYPE_CUBE";if(i.envMap)switch(i.envMapMode){case Ps:case Ls:t="ENVMAP_TYPE_CUBE";break;case Ba:t="ENVMAP_TYPE_CUBE_UV";break}return t}function s0(i){let t="ENVMAP_MODE_REFLECTION";if(i.envMap)switch(i.envMapMode){case Ls:t="ENVMAP_MODE_REFRACTION";break}return t}function r0(i){let t="ENVMAP_BLENDING_NONE";if(i.envMap)switch(i.combine){case ka:t="ENVMAP_BLENDING_MULTIPLY";break;case Wd:t="ENVMAP_BLENDING_MIX";break;case Xd:t="ENVMAP_BLENDING_ADD";break}return t}function a0(i){const t=i.envMapCubeUVHeight;if(t===null)return null;const e=Math.log2(t)-2,n=1/t;return{texelWidth:1/(3*Math.max(Math.pow(2,e),112)),texelHeight:n,maxMip:e}}function o0(i,t,e,n){const s=i.getContext(),r=e.defines;let a=e.vertexShader,o=e.fragmentShader;const c=n0(e),l=i0(e),h=s0(e),u=r0(e),d=a0(e),f=Y_(e),g=$_(r),_=s.createProgram();let m,p,P=e.glslVersion?"#version "+e.glslVersion+`
`:"";e.isRawShaderMaterial?(m=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(ar).join(`
`),m.length>0&&(m+=`
`),p=["#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g].filter(ar).join(`
`),p.length>0&&(p+=`
`)):(m=[dh(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",e.batching?"#define USE_BATCHING":"",e.batchingColor?"#define USE_BATCHING_COLOR":"",e.instancing?"#define USE_INSTANCING":"",e.instancingColor?"#define USE_INSTANCING_COLOR":"",e.instancingMorph?"#define USE_INSTANCING_MORPH":"",e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.map?"#define USE_MAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+h:"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.displacementMap?"#define USE_DISPLACEMENTMAP":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.mapUv?"#define MAP_UV "+e.mapUv:"",e.alphaMapUv?"#define ALPHAMAP_UV "+e.alphaMapUv:"",e.lightMapUv?"#define LIGHTMAP_UV "+e.lightMapUv:"",e.aoMapUv?"#define AOMAP_UV "+e.aoMapUv:"",e.emissiveMapUv?"#define EMISSIVEMAP_UV "+e.emissiveMapUv:"",e.bumpMapUv?"#define BUMPMAP_UV "+e.bumpMapUv:"",e.normalMapUv?"#define NORMALMAP_UV "+e.normalMapUv:"",e.displacementMapUv?"#define DISPLACEMENTMAP_UV "+e.displacementMapUv:"",e.metalnessMapUv?"#define METALNESSMAP_UV "+e.metalnessMapUv:"",e.roughnessMapUv?"#define ROUGHNESSMAP_UV "+e.roughnessMapUv:"",e.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+e.anisotropyMapUv:"",e.clearcoatMapUv?"#define CLEARCOATMAP_UV "+e.clearcoatMapUv:"",e.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+e.clearcoatNormalMapUv:"",e.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+e.clearcoatRoughnessMapUv:"",e.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+e.iridescenceMapUv:"",e.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+e.iridescenceThicknessMapUv:"",e.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+e.sheenColorMapUv:"",e.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+e.sheenRoughnessMapUv:"",e.specularMapUv?"#define SPECULARMAP_UV "+e.specularMapUv:"",e.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+e.specularColorMapUv:"",e.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+e.specularIntensityMapUv:"",e.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+e.transmissionMapUv:"",e.thicknessMapUv?"#define THICKNESSMAP_UV "+e.thicknessMapUv:"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.flatShading?"#define FLAT_SHADED":"",e.skinning?"#define USE_SKINNING":"",e.morphTargets?"#define USE_MORPHTARGETS":"",e.morphNormals&&e.flatShading===!1?"#define USE_MORPHNORMALS":"",e.morphColors?"#define USE_MORPHCOLORS":"",e.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+e.morphTextureStride:"",e.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+e.morphTargetsCount:"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+c:"",e.sizeAttenuation?"#define USE_SIZEATTENUATION":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(ar).join(`
`),p=[dh(e),"#define SHADER_TYPE "+e.shaderType,"#define SHADER_NAME "+e.shaderName,g,e.useFog&&e.fog?"#define USE_FOG":"",e.useFog&&e.fogExp2?"#define FOG_EXP2":"",e.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",e.map?"#define USE_MAP":"",e.matcap?"#define USE_MATCAP":"",e.envMap?"#define USE_ENVMAP":"",e.envMap?"#define "+l:"",e.envMap?"#define "+h:"",e.envMap?"#define "+u:"",d?"#define CUBEUV_TEXEL_WIDTH "+d.texelWidth:"",d?"#define CUBEUV_TEXEL_HEIGHT "+d.texelHeight:"",d?"#define CUBEUV_MAX_MIP "+d.maxMip+".0":"",e.lightMap?"#define USE_LIGHTMAP":"",e.aoMap?"#define USE_AOMAP":"",e.bumpMap?"#define USE_BUMPMAP":"",e.normalMap?"#define USE_NORMALMAP":"",e.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",e.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",e.emissiveMap?"#define USE_EMISSIVEMAP":"",e.anisotropy?"#define USE_ANISOTROPY":"",e.anisotropyMap?"#define USE_ANISOTROPYMAP":"",e.clearcoat?"#define USE_CLEARCOAT":"",e.clearcoatMap?"#define USE_CLEARCOATMAP":"",e.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",e.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",e.dispersion?"#define USE_DISPERSION":"",e.iridescence?"#define USE_IRIDESCENCE":"",e.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",e.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",e.specularMap?"#define USE_SPECULARMAP":"",e.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",e.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",e.roughnessMap?"#define USE_ROUGHNESSMAP":"",e.metalnessMap?"#define USE_METALNESSMAP":"",e.alphaMap?"#define USE_ALPHAMAP":"",e.alphaTest?"#define USE_ALPHATEST":"",e.alphaHash?"#define USE_ALPHAHASH":"",e.sheen?"#define USE_SHEEN":"",e.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",e.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",e.transmission?"#define USE_TRANSMISSION":"",e.transmissionMap?"#define USE_TRANSMISSIONMAP":"",e.thicknessMap?"#define USE_THICKNESSMAP":"",e.vertexTangents&&e.flatShading===!1?"#define USE_TANGENT":"",e.vertexColors||e.instancingColor||e.batchingColor?"#define USE_COLOR":"",e.vertexAlphas?"#define USE_COLOR_ALPHA":"",e.vertexUv1s?"#define USE_UV1":"",e.vertexUv2s?"#define USE_UV2":"",e.vertexUv3s?"#define USE_UV3":"",e.pointsUvs?"#define USE_POINTS_UV":"",e.gradientMap?"#define USE_GRADIENTMAP":"",e.flatShading?"#define FLAT_SHADED":"",e.doubleSided?"#define DOUBLE_SIDED":"",e.flipSided?"#define FLIP_SIDED":"",e.shadowMapEnabled?"#define USE_SHADOWMAP":"",e.shadowMapEnabled?"#define "+c:"",e.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",e.numLightProbes>0?"#define USE_LIGHT_PROBES":"",e.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",e.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",e.logarithmicDepthBuffer?"#define USE_LOGDEPTHBUF":"",e.reverseDepthBuffer?"#define USE_REVERSEDEPTHBUF":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",e.toneMapping!==Li?"#define TONE_MAPPING":"",e.toneMapping!==Li?ae.tonemapping_pars_fragment:"",e.toneMapping!==Li?q_("toneMapping",e.toneMapping):"",e.dithering?"#define DITHERING":"",e.opaque?"#define OPAQUE":"",ae.colorspace_pars_fragment,X_("linearToOutputTexel",e.outputColorSpace),j_(),e.useDepthPacking?"#define DEPTH_PACKING "+e.depthPacking:"",`
`].filter(ar).join(`
`)),a=Dc(a),a=lh(a,e),a=hh(a,e),o=Dc(o),o=lh(o,e),o=hh(o,e),a=uh(a),o=uh(o),e.isRawShaderMaterial!==!0&&(P=`#version 300 es
`,m=[f,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+m,p=["#define varying in",e.glslVersion===El?"":"layout(location = 0) out highp vec4 pc_fragColor;",e.glslVersion===El?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+p);const w=P+m+a,y=P+p+o,N=ah(s,s.VERTEX_SHADER,w),C=ah(s,s.FRAGMENT_SHADER,y);s.attachShader(_,N),s.attachShader(_,C),e.index0AttributeName!==void 0?s.bindAttribLocation(_,0,e.index0AttributeName):e.morphTargets===!0&&s.bindAttribLocation(_,0,"position"),s.linkProgram(_);function L(F){if(i.debug.checkShaderErrors){const k=s.getProgramInfoLog(_).trim(),H=s.getShaderInfoLog(N).trim(),Z=s.getShaderInfoLog(C).trim();let tt=!0,O=!0;if(s.getProgramParameter(_,s.LINK_STATUS)===!1)if(tt=!1,typeof i.debug.onShaderError=="function")i.debug.onShaderError(s,_,N,C);else{const et=ch(s,N,"vertex"),W=ch(s,C,"fragment");console.error("THREE.WebGLProgram: Shader Error "+s.getError()+" - VALIDATE_STATUS "+s.getProgramParameter(_,s.VALIDATE_STATUS)+`

Material Name: `+F.name+`
Material Type: `+F.type+`

Program Info Log: `+k+`
`+et+`
`+W)}else k!==""?console.warn("THREE.WebGLProgram: Program Info Log:",k):(H===""||Z==="")&&(O=!1);O&&(F.diagnostics={runnable:tt,programLog:k,vertexShader:{log:H,prefix:m},fragmentShader:{log:Z,prefix:p}})}s.deleteShader(N),s.deleteShader(C),I=new xa(s,_),M=K_(s,_)}let I;this.getUniforms=function(){return I===void 0&&L(this),I};let M;this.getAttributes=function(){return M===void 0&&L(this),M};let b=e.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return b===!1&&(b=s.getProgramParameter(_,V_)),b},this.destroy=function(){n.releaseStatesOfProgram(this),s.deleteProgram(_),this.program=void 0},this.type=e.shaderType,this.name=e.shaderName,this.id=H_++,this.cacheKey=t,this.usedTimes=1,this.program=_,this.vertexShader=N,this.fragmentShader=C,this}let c0=0;class l0{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(t){const e=t.vertexShader,n=t.fragmentShader,s=this._getShaderStage(e),r=this._getShaderStage(n),a=this._getShaderCacheForMaterial(t);return a.has(s)===!1&&(a.add(s),s.usedTimes++),a.has(r)===!1&&(a.add(r),r.usedTimes++),this}remove(t){const e=this.materialCache.get(t);for(const n of e)n.usedTimes--,n.usedTimes===0&&this.shaderCache.delete(n.code);return this.materialCache.delete(t),this}getVertexShaderID(t){return this._getShaderStage(t.vertexShader).id}getFragmentShaderID(t){return this._getShaderStage(t.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(t){const e=this.materialCache;let n=e.get(t);return n===void 0&&(n=new Set,e.set(t,n)),n}_getShaderStage(t){const e=this.shaderCache;let n=e.get(t);return n===void 0&&(n=new h0(t),e.set(t,n)),n}}class h0{constructor(t){this.id=c0++,this.code=t,this.usedTimes=0}}function u0(i,t,e,n,s,r,a){const o=new jc,c=new l0,l=new Set,h=[],u=s.logarithmicDepthBuffer,d=s.vertexTextures;let f=s.precision;const g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function _(M){return l.add(M),M===0?"uv":`uv${M}`}function m(M,b,F,k,H){const Z=k.fog,tt=H.geometry,O=M.isMeshStandardMaterial?k.environment:null,et=(M.isMeshStandardMaterial?e:t).get(M.envMap||O),W=et&&et.mapping===Ba?et.image.height:null,lt=g[M.type];M.precision!==null&&(f=s.getMaxPrecision(M.precision),f!==M.precision&&console.warn("THREE.WebGLProgram.getParameters:",M.precision,"not supported, using",f,"instead."));const pt=tt.morphAttributes.position||tt.morphAttributes.normal||tt.morphAttributes.color,mt=pt!==void 0?pt.length:0;let Rt=0;tt.morphAttributes.position!==void 0&&(Rt=1),tt.morphAttributes.normal!==void 0&&(Rt=2),tt.morphAttributes.color!==void 0&&(Rt=3);let wt,q,J,nt;if(lt){const se=Xn[lt];wt=se.vertexShader,q=se.fragmentShader}else wt=M.vertexShader,q=M.fragmentShader,c.update(M),J=c.getVertexShaderID(M),nt=c.getFragmentShaderID(M);const it=i.getRenderTarget(),vt=i.state.buffers.depth.getReversed(),zt=H.isInstancedMesh===!0,Qt=H.isBatchedMesh===!0,Re=!!M.map,ue=!!M.matcap,Ie=!!et,G=!!M.aoMap,on=!!M.lightMap,oe=!!M.bumpMap,ce=!!M.normalMap,Wt=!!M.displacementMap,Ae=!!M.emissiveMap,Ht=!!M.metalnessMap,U=!!M.roughnessMap,S=M.anisotropy>0,j=M.clearcoat>0,at=M.dispersion>0,ht=M.iridescence>0,rt=M.sheen>0,Ft=M.transmission>0,Mt=S&&!!M.anisotropyMap,Ct=j&&!!M.clearcoatMap,de=j&&!!M.clearcoatNormalMap,ft=j&&!!M.clearcoatRoughnessMap,Pt=ht&&!!M.iridescenceMap,Xt=ht&&!!M.iridescenceThicknessMap,$t=rt&&!!M.sheenColorMap,Lt=rt&&!!M.sheenRoughnessMap,he=!!M.specularMap,ne=!!M.specularColorMap,Me=!!M.specularIntensityMap,z=Ft&&!!M.transmissionMap,xt=Ft&&!!M.thicknessMap,Q=!!M.gradientMap,ot=!!M.alphaMap,Et=M.alphaTest>0,bt=!!M.alphaHash,te=!!M.extensions;let Pe=Li;M.toneMapped&&(it===null||it.isXRRenderTarget===!0)&&(Pe=i.toneMapping);const qe={shaderID:lt,shaderType:M.type,shaderName:M.name,vertexShader:wt,fragmentShader:q,defines:M.defines,customVertexShaderID:J,customFragmentShaderID:nt,isRawShaderMaterial:M.isRawShaderMaterial===!0,glslVersion:M.glslVersion,precision:f,batching:Qt,batchingColor:Qt&&H._colorsTexture!==null,instancing:zt,instancingColor:zt&&H.instanceColor!==null,instancingMorph:zt&&H.morphTexture!==null,supportsVertexTextures:d,outputColorSpace:it===null?i.outputColorSpace:it.isXRRenderTarget===!0?it.texture.colorSpace:Hs,alphaToCoverage:!!M.alphaToCoverage,map:Re,matcap:ue,envMap:Ie,envMapMode:Ie&&et.mapping,envMapCubeUVHeight:W,aoMap:G,lightMap:on,bumpMap:oe,normalMap:ce,displacementMap:d&&Wt,emissiveMap:Ae,normalMapObjectSpace:ce&&M.normalMapType===sf,normalMapTangentSpace:ce&&M.normalMapType===za,metalnessMap:Ht,roughnessMap:U,anisotropy:S,anisotropyMap:Mt,clearcoat:j,clearcoatMap:Ct,clearcoatNormalMap:de,clearcoatRoughnessMap:ft,dispersion:at,iridescence:ht,iridescenceMap:Pt,iridescenceThicknessMap:Xt,sheen:rt,sheenColorMap:$t,sheenRoughnessMap:Lt,specularMap:he,specularColorMap:ne,specularIntensityMap:Me,transmission:Ft,transmissionMap:z,thicknessMap:xt,gradientMap:Q,opaque:M.transparent===!1&&M.blending===Ss&&M.alphaToCoverage===!1,alphaMap:ot,alphaTest:Et,alphaHash:bt,combine:M.combine,mapUv:Re&&_(M.map.channel),aoMapUv:G&&_(M.aoMap.channel),lightMapUv:on&&_(M.lightMap.channel),bumpMapUv:oe&&_(M.bumpMap.channel),normalMapUv:ce&&_(M.normalMap.channel),displacementMapUv:Wt&&_(M.displacementMap.channel),emissiveMapUv:Ae&&_(M.emissiveMap.channel),metalnessMapUv:Ht&&_(M.metalnessMap.channel),roughnessMapUv:U&&_(M.roughnessMap.channel),anisotropyMapUv:Mt&&_(M.anisotropyMap.channel),clearcoatMapUv:Ct&&_(M.clearcoatMap.channel),clearcoatNormalMapUv:de&&_(M.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:ft&&_(M.clearcoatRoughnessMap.channel),iridescenceMapUv:Pt&&_(M.iridescenceMap.channel),iridescenceThicknessMapUv:Xt&&_(M.iridescenceThicknessMap.channel),sheenColorMapUv:$t&&_(M.sheenColorMap.channel),sheenRoughnessMapUv:Lt&&_(M.sheenRoughnessMap.channel),specularMapUv:he&&_(M.specularMap.channel),specularColorMapUv:ne&&_(M.specularColorMap.channel),specularIntensityMapUv:Me&&_(M.specularIntensityMap.channel),transmissionMapUv:z&&_(M.transmissionMap.channel),thicknessMapUv:xt&&_(M.thicknessMap.channel),alphaMapUv:ot&&_(M.alphaMap.channel),vertexTangents:!!tt.attributes.tangent&&(ce||S),vertexColors:M.vertexColors,vertexAlphas:M.vertexColors===!0&&!!tt.attributes.color&&tt.attributes.color.itemSize===4,pointsUvs:H.isPoints===!0&&!!tt.attributes.uv&&(Re||ot),fog:!!Z,useFog:M.fog===!0,fogExp2:!!Z&&Z.isFogExp2,flatShading:M.flatShading===!0,sizeAttenuation:M.sizeAttenuation===!0,logarithmicDepthBuffer:u,reverseDepthBuffer:vt,skinning:H.isSkinnedMesh===!0,morphTargets:tt.morphAttributes.position!==void 0,morphNormals:tt.morphAttributes.normal!==void 0,morphColors:tt.morphAttributes.color!==void 0,morphTargetsCount:mt,morphTextureStride:Rt,numDirLights:b.directional.length,numPointLights:b.point.length,numSpotLights:b.spot.length,numSpotLightMaps:b.spotLightMap.length,numRectAreaLights:b.rectArea.length,numHemiLights:b.hemi.length,numDirLightShadows:b.directionalShadowMap.length,numPointLightShadows:b.pointShadowMap.length,numSpotLightShadows:b.spotShadowMap.length,numSpotLightShadowsWithMaps:b.numSpotLightShadowsWithMaps,numLightProbes:b.numLightProbes,numClippingPlanes:a.numPlanes,numClipIntersection:a.numIntersection,dithering:M.dithering,shadowMapEnabled:i.shadowMap.enabled&&F.length>0,shadowMapType:i.shadowMap.type,toneMapping:Pe,decodeVideoTexture:Re&&M.map.isVideoTexture===!0&&le.getTransfer(M.map.colorSpace)===we,decodeVideoTextureEmissive:Ae&&M.emissiveMap.isVideoTexture===!0&&le.getTransfer(M.emissiveMap.colorSpace)===we,premultipliedAlpha:M.premultipliedAlpha,doubleSided:M.side===dn,flipSided:M.side===fn,useDepthPacking:M.depthPacking>=0,depthPacking:M.depthPacking||0,index0AttributeName:M.index0AttributeName,extensionClipCullDistance:te&&M.extensions.clipCullDistance===!0&&n.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(te&&M.extensions.multiDraw===!0||Qt)&&n.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:n.has("KHR_parallel_shader_compile"),customProgramCacheKey:M.customProgramCacheKey()};return qe.vertexUv1s=l.has(1),qe.vertexUv2s=l.has(2),qe.vertexUv3s=l.has(3),l.clear(),qe}function p(M){const b=[];if(M.shaderID?b.push(M.shaderID):(b.push(M.customVertexShaderID),b.push(M.customFragmentShaderID)),M.defines!==void 0)for(const F in M.defines)b.push(F),b.push(M.defines[F]);return M.isRawShaderMaterial===!1&&(P(b,M),w(b,M),b.push(i.outputColorSpace)),b.push(M.customProgramCacheKey),b.join()}function P(M,b){M.push(b.precision),M.push(b.outputColorSpace),M.push(b.envMapMode),M.push(b.envMapCubeUVHeight),M.push(b.mapUv),M.push(b.alphaMapUv),M.push(b.lightMapUv),M.push(b.aoMapUv),M.push(b.bumpMapUv),M.push(b.normalMapUv),M.push(b.displacementMapUv),M.push(b.emissiveMapUv),M.push(b.metalnessMapUv),M.push(b.roughnessMapUv),M.push(b.anisotropyMapUv),M.push(b.clearcoatMapUv),M.push(b.clearcoatNormalMapUv),M.push(b.clearcoatRoughnessMapUv),M.push(b.iridescenceMapUv),M.push(b.iridescenceThicknessMapUv),M.push(b.sheenColorMapUv),M.push(b.sheenRoughnessMapUv),M.push(b.specularMapUv),M.push(b.specularColorMapUv),M.push(b.specularIntensityMapUv),M.push(b.transmissionMapUv),M.push(b.thicknessMapUv),M.push(b.combine),M.push(b.fogExp2),M.push(b.sizeAttenuation),M.push(b.morphTargetsCount),M.push(b.morphAttributeCount),M.push(b.numDirLights),M.push(b.numPointLights),M.push(b.numSpotLights),M.push(b.numSpotLightMaps),M.push(b.numHemiLights),M.push(b.numRectAreaLights),M.push(b.numDirLightShadows),M.push(b.numPointLightShadows),M.push(b.numSpotLightShadows),M.push(b.numSpotLightShadowsWithMaps),M.push(b.numLightProbes),M.push(b.shadowMapType),M.push(b.toneMapping),M.push(b.numClippingPlanes),M.push(b.numClipIntersection),M.push(b.depthPacking)}function w(M,b){o.disableAll(),b.supportsVertexTextures&&o.enable(0),b.instancing&&o.enable(1),b.instancingColor&&o.enable(2),b.instancingMorph&&o.enable(3),b.matcap&&o.enable(4),b.envMap&&o.enable(5),b.normalMapObjectSpace&&o.enable(6),b.normalMapTangentSpace&&o.enable(7),b.clearcoat&&o.enable(8),b.iridescence&&o.enable(9),b.alphaTest&&o.enable(10),b.vertexColors&&o.enable(11),b.vertexAlphas&&o.enable(12),b.vertexUv1s&&o.enable(13),b.vertexUv2s&&o.enable(14),b.vertexUv3s&&o.enable(15),b.vertexTangents&&o.enable(16),b.anisotropy&&o.enable(17),b.alphaHash&&o.enable(18),b.batching&&o.enable(19),b.dispersion&&o.enable(20),b.batchingColor&&o.enable(21),M.push(o.mask),o.disableAll(),b.fog&&o.enable(0),b.useFog&&o.enable(1),b.flatShading&&o.enable(2),b.logarithmicDepthBuffer&&o.enable(3),b.reverseDepthBuffer&&o.enable(4),b.skinning&&o.enable(5),b.morphTargets&&o.enable(6),b.morphNormals&&o.enable(7),b.morphColors&&o.enable(8),b.premultipliedAlpha&&o.enable(9),b.shadowMapEnabled&&o.enable(10),b.doubleSided&&o.enable(11),b.flipSided&&o.enable(12),b.useDepthPacking&&o.enable(13),b.dithering&&o.enable(14),b.transmission&&o.enable(15),b.sheen&&o.enable(16),b.opaque&&o.enable(17),b.pointsUvs&&o.enable(18),b.decodeVideoTexture&&o.enable(19),b.decodeVideoTextureEmissive&&o.enable(20),b.alphaToCoverage&&o.enable(21),M.push(o.mask)}function y(M){const b=g[M.type];let F;if(b){const k=Xn[b];F=Yf.clone(k.uniforms)}else F=M.uniforms;return F}function N(M,b){let F;for(let k=0,H=h.length;k<H;k++){const Z=h[k];if(Z.cacheKey===b){F=Z,++F.usedTimes;break}}return F===void 0&&(F=new o0(i,b,M,r),h.push(F)),F}function C(M){if(--M.usedTimes===0){const b=h.indexOf(M);h[b]=h[h.length-1],h.pop(),M.destroy()}}function L(M){c.remove(M)}function I(){c.dispose()}return{getParameters:m,getProgramCacheKey:p,getUniforms:y,acquireProgram:N,releaseProgram:C,releaseShaderCache:L,programs:h,dispose:I}}function d0(){let i=new WeakMap;function t(a){return i.has(a)}function e(a){let o=i.get(a);return o===void 0&&(o={},i.set(a,o)),o}function n(a){i.delete(a)}function s(a,o,c){i.get(a)[o]=c}function r(){i=new WeakMap}return{has:t,get:e,remove:n,update:s,dispose:r}}function f0(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.material.id!==t.material.id?i.material.id-t.material.id:i.z!==t.z?i.z-t.z:i.id-t.id}function fh(i,t){return i.groupOrder!==t.groupOrder?i.groupOrder-t.groupOrder:i.renderOrder!==t.renderOrder?i.renderOrder-t.renderOrder:i.z!==t.z?t.z-i.z:i.id-t.id}function ph(){const i=[];let t=0;const e=[],n=[],s=[];function r(){t=0,e.length=0,n.length=0,s.length=0}function a(u,d,f,g,_,m){let p=i[t];return p===void 0?(p={id:u.id,object:u,geometry:d,material:f,groupOrder:g,renderOrder:u.renderOrder,z:_,group:m},i[t]=p):(p.id=u.id,p.object=u,p.geometry=d,p.material=f,p.groupOrder=g,p.renderOrder=u.renderOrder,p.z=_,p.group=m),t++,p}function o(u,d,f,g,_,m){const p=a(u,d,f,g,_,m);f.transmission>0?n.push(p):f.transparent===!0?s.push(p):e.push(p)}function c(u,d,f,g,_,m){const p=a(u,d,f,g,_,m);f.transmission>0?n.unshift(p):f.transparent===!0?s.unshift(p):e.unshift(p)}function l(u,d){e.length>1&&e.sort(u||f0),n.length>1&&n.sort(d||fh),s.length>1&&s.sort(d||fh)}function h(){for(let u=t,d=i.length;u<d;u++){const f=i[u];if(f.id===null)break;f.id=null,f.object=null,f.geometry=null,f.material=null,f.group=null}}return{opaque:e,transmissive:n,transparent:s,init:r,push:o,unshift:c,finish:h,sort:l}}function p0(){let i=new WeakMap;function t(n,s){const r=i.get(n);let a;return r===void 0?(a=new ph,i.set(n,[a])):s>=r.length?(a=new ph,r.push(a)):a=r[s],a}function e(){i=new WeakMap}return{get:t,dispose:e}}function m0(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={direction:new D,color:new Jt};break;case"SpotLight":e={position:new D,direction:new D,color:new Jt,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":e={position:new D,color:new Jt,distance:0,decay:0};break;case"HemisphereLight":e={direction:new D,skyColor:new Jt,groundColor:new Jt};break;case"RectAreaLight":e={color:new Jt,position:new D,halfWidth:new D,halfHeight:new D};break}return i[t.id]=e,e}}}function g0(){const i={};return{get:function(t){if(i[t.id]!==void 0)return i[t.id];let e;switch(t.type){case"DirectionalLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At};break;case"SpotLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At};break;case"PointLight":e={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new At,shadowCameraNear:1,shadowCameraFar:1e3};break}return i[t.id]=e,e}}}let _0=0;function v0(i,t){return(t.castShadow?2:0)-(i.castShadow?2:0)+(t.map?1:0)-(i.map?1:0)}function x0(i){const t=new m0,e=g0(),n={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let l=0;l<9;l++)n.probe.push(new D);const s=new D,r=new Yt,a=new Yt;function o(l){let h=0,u=0,d=0;for(let M=0;M<9;M++)n.probe[M].set(0,0,0);let f=0,g=0,_=0,m=0,p=0,P=0,w=0,y=0,N=0,C=0,L=0;l.sort(v0);for(let M=0,b=l.length;M<b;M++){const F=l[M],k=F.color,H=F.intensity,Z=F.distance,tt=F.shadow&&F.shadow.map?F.shadow.map.texture:null;if(F.isAmbientLight)h+=k.r*H,u+=k.g*H,d+=k.b*H;else if(F.isLightProbe){for(let O=0;O<9;O++)n.probe[O].addScaledVector(F.sh.coefficients[O],H);L++}else if(F.isDirectionalLight){const O=t.get(F);if(O.color.copy(F.color).multiplyScalar(F.intensity),F.castShadow){const et=F.shadow,W=e.get(F);W.shadowIntensity=et.intensity,W.shadowBias=et.bias,W.shadowNormalBias=et.normalBias,W.shadowRadius=et.radius,W.shadowMapSize=et.mapSize,n.directionalShadow[f]=W,n.directionalShadowMap[f]=tt,n.directionalShadowMatrix[f]=F.shadow.matrix,P++}n.directional[f]=O,f++}else if(F.isSpotLight){const O=t.get(F);O.position.setFromMatrixPosition(F.matrixWorld),O.color.copy(k).multiplyScalar(H),O.distance=Z,O.coneCos=Math.cos(F.angle),O.penumbraCos=Math.cos(F.angle*(1-F.penumbra)),O.decay=F.decay,n.spot[_]=O;const et=F.shadow;if(F.map&&(n.spotLightMap[N]=F.map,N++,et.updateMatrices(F),F.castShadow&&C++),n.spotLightMatrix[_]=et.matrix,F.castShadow){const W=e.get(F);W.shadowIntensity=et.intensity,W.shadowBias=et.bias,W.shadowNormalBias=et.normalBias,W.shadowRadius=et.radius,W.shadowMapSize=et.mapSize,n.spotShadow[_]=W,n.spotShadowMap[_]=tt,y++}_++}else if(F.isRectAreaLight){const O=t.get(F);O.color.copy(k).multiplyScalar(H),O.halfWidth.set(F.width*.5,0,0),O.halfHeight.set(0,F.height*.5,0),n.rectArea[m]=O,m++}else if(F.isPointLight){const O=t.get(F);if(O.color.copy(F.color).multiplyScalar(F.intensity),O.distance=F.distance,O.decay=F.decay,F.castShadow){const et=F.shadow,W=e.get(F);W.shadowIntensity=et.intensity,W.shadowBias=et.bias,W.shadowNormalBias=et.normalBias,W.shadowRadius=et.radius,W.shadowMapSize=et.mapSize,W.shadowCameraNear=et.camera.near,W.shadowCameraFar=et.camera.far,n.pointShadow[g]=W,n.pointShadowMap[g]=tt,n.pointShadowMatrix[g]=F.shadow.matrix,w++}n.point[g]=O,g++}else if(F.isHemisphereLight){const O=t.get(F);O.skyColor.copy(F.color).multiplyScalar(H),O.groundColor.copy(F.groundColor).multiplyScalar(H),n.hemi[p]=O,p++}}m>0&&(i.has("OES_texture_float_linear")===!0?(n.rectAreaLTC1=_t.LTC_FLOAT_1,n.rectAreaLTC2=_t.LTC_FLOAT_2):(n.rectAreaLTC1=_t.LTC_HALF_1,n.rectAreaLTC2=_t.LTC_HALF_2)),n.ambient[0]=h,n.ambient[1]=u,n.ambient[2]=d;const I=n.hash;(I.directionalLength!==f||I.pointLength!==g||I.spotLength!==_||I.rectAreaLength!==m||I.hemiLength!==p||I.numDirectionalShadows!==P||I.numPointShadows!==w||I.numSpotShadows!==y||I.numSpotMaps!==N||I.numLightProbes!==L)&&(n.directional.length=f,n.spot.length=_,n.rectArea.length=m,n.point.length=g,n.hemi.length=p,n.directionalShadow.length=P,n.directionalShadowMap.length=P,n.pointShadow.length=w,n.pointShadowMap.length=w,n.spotShadow.length=y,n.spotShadowMap.length=y,n.directionalShadowMatrix.length=P,n.pointShadowMatrix.length=w,n.spotLightMatrix.length=y+N-C,n.spotLightMap.length=N,n.numSpotLightShadowsWithMaps=C,n.numLightProbes=L,I.directionalLength=f,I.pointLength=g,I.spotLength=_,I.rectAreaLength=m,I.hemiLength=p,I.numDirectionalShadows=P,I.numPointShadows=w,I.numSpotShadows=y,I.numSpotMaps=N,I.numLightProbes=L,n.version=_0++)}function c(l,h){let u=0,d=0,f=0,g=0,_=0;const m=h.matrixWorldInverse;for(let p=0,P=l.length;p<P;p++){const w=l[p];if(w.isDirectionalLight){const y=n.directional[u];y.direction.setFromMatrixPosition(w.matrixWorld),s.setFromMatrixPosition(w.target.matrixWorld),y.direction.sub(s),y.direction.transformDirection(m),u++}else if(w.isSpotLight){const y=n.spot[f];y.position.setFromMatrixPosition(w.matrixWorld),y.position.applyMatrix4(m),y.direction.setFromMatrixPosition(w.matrixWorld),s.setFromMatrixPosition(w.target.matrixWorld),y.direction.sub(s),y.direction.transformDirection(m),f++}else if(w.isRectAreaLight){const y=n.rectArea[g];y.position.setFromMatrixPosition(w.matrixWorld),y.position.applyMatrix4(m),a.identity(),r.copy(w.matrixWorld),r.premultiply(m),a.extractRotation(r),y.halfWidth.set(w.width*.5,0,0),y.halfHeight.set(0,w.height*.5,0),y.halfWidth.applyMatrix4(a),y.halfHeight.applyMatrix4(a),g++}else if(w.isPointLight){const y=n.point[d];y.position.setFromMatrixPosition(w.matrixWorld),y.position.applyMatrix4(m),d++}else if(w.isHemisphereLight){const y=n.hemi[_];y.direction.setFromMatrixPosition(w.matrixWorld),y.direction.transformDirection(m),_++}}}return{setup:o,setupView:c,state:n}}function mh(i){const t=new x0(i),e=[],n=[];function s(h){l.camera=h,e.length=0,n.length=0}function r(h){e.push(h)}function a(h){n.push(h)}function o(){t.setup(e)}function c(h){t.setupView(e,h)}const l={lightsArray:e,shadowsArray:n,camera:null,lights:t,transmissionRenderTarget:{}};return{init:s,state:l,setupLights:o,setupLightsView:c,pushLight:r,pushShadow:a}}function y0(i){let t=new WeakMap;function e(s,r=0){const a=t.get(s);let o;return a===void 0?(o=new mh(i),t.set(s,[o])):r>=a.length?(o=new mh(i),a.push(o)):o=a[r],o}function n(){t=new WeakMap}return{get:e,dispose:n}}class M0 extends Hn{static get type(){return"MeshDepthMaterial"}constructor(t){super(),this.isMeshDepthMaterial=!0,this.depthPacking=ef,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(t)}copy(t){return super.copy(t),this.depthPacking=t.depthPacking,this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this}}class b0 extends Hn{static get type(){return"MeshDistanceMaterial"}constructor(t){super(),this.isMeshDistanceMaterial=!0,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(t)}copy(t){return super.copy(t),this.map=t.map,this.alphaMap=t.alphaMap,this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this}}const S0=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,E0=`uniform sampler2D shadow_pass;
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
}`;function w0(i,t,e){let n=new Yc;const s=new At,r=new At,a=new ye,o=new M0({depthPacking:nf}),c=new b0,l={},h=e.maxTextureSize,u={[di]:fn,[fn]:di,[dn]:dn},d=new Ni({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new At},radius:{value:4}},vertexShader:S0,fragmentShader:E0}),f=d.clone();f.defines.HORIZONTAL_PASS=1;const g=new Le;g.setAttribute("position",new bn(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));const _=new ge(g,d),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=nu;let p=this.type;this.render=function(C,L,I){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||C.length===0)return;const M=i.getRenderTarget(),b=i.getActiveCubeFace(),F=i.getActiveMipmapLevel(),k=i.state;k.setBlending(Pi),k.buffers.color.setClear(1,1,1,1),k.buffers.depth.setTest(!0),k.setScissorTest(!1);const H=p!==oi&&this.type===oi,Z=p===oi&&this.type!==oi;for(let tt=0,O=C.length;tt<O;tt++){const et=C[tt],W=et.shadow;if(W===void 0){console.warn("THREE.WebGLShadowMap:",et,"has no shadow.");continue}if(W.autoUpdate===!1&&W.needsUpdate===!1)continue;s.copy(W.mapSize);const lt=W.getFrameExtents();if(s.multiply(lt),r.copy(W.mapSize),(s.x>h||s.y>h)&&(s.x>h&&(r.x=Math.floor(h/lt.x),s.x=r.x*lt.x,W.mapSize.x=r.x),s.y>h&&(r.y=Math.floor(h/lt.y),s.y=r.y*lt.y,W.mapSize.y=r.y)),W.map===null||H===!0||Z===!0){const mt=this.type!==oi?{minFilter:Mn,magFilter:Mn}:{};W.map!==null&&W.map.dispose(),W.map=new Ji(s.x,s.y,mt),W.map.texture.name=et.name+".shadowMap",W.camera.updateProjectionMatrix()}i.setRenderTarget(W.map),i.clear();const pt=W.getViewportCount();for(let mt=0;mt<pt;mt++){const Rt=W.getViewport(mt);a.set(r.x*Rt.x,r.y*Rt.y,r.x*Rt.z,r.y*Rt.w),k.viewport(a),W.updateMatrices(et,mt),n=W.getFrustum(),y(L,I,W.camera,et,this.type)}W.isPointLightShadow!==!0&&this.type===oi&&P(W,I),W.needsUpdate=!1}p=this.type,m.needsUpdate=!1,i.setRenderTarget(M,b,F)};function P(C,L){const I=t.update(_);d.defines.VSM_SAMPLES!==C.blurSamples&&(d.defines.VSM_SAMPLES=C.blurSamples,f.defines.VSM_SAMPLES=C.blurSamples,d.needsUpdate=!0,f.needsUpdate=!0),C.mapPass===null&&(C.mapPass=new Ji(s.x,s.y)),d.uniforms.shadow_pass.value=C.map.texture,d.uniforms.resolution.value=C.mapSize,d.uniforms.radius.value=C.radius,i.setRenderTarget(C.mapPass),i.clear(),i.renderBufferDirect(L,null,I,d,_,null),f.uniforms.shadow_pass.value=C.mapPass.texture,f.uniforms.resolution.value=C.mapSize,f.uniforms.radius.value=C.radius,i.setRenderTarget(C.map),i.clear(),i.renderBufferDirect(L,null,I,f,_,null)}function w(C,L,I,M){let b=null;const F=I.isPointLight===!0?C.customDistanceMaterial:C.customDepthMaterial;if(F!==void 0)b=F;else if(b=I.isPointLight===!0?c:o,i.localClippingEnabled&&L.clipShadows===!0&&Array.isArray(L.clippingPlanes)&&L.clippingPlanes.length!==0||L.displacementMap&&L.displacementScale!==0||L.alphaMap&&L.alphaTest>0||L.map&&L.alphaTest>0){const k=b.uuid,H=L.uuid;let Z=l[k];Z===void 0&&(Z={},l[k]=Z);let tt=Z[H];tt===void 0&&(tt=b.clone(),Z[H]=tt,L.addEventListener("dispose",N)),b=tt}if(b.visible=L.visible,b.wireframe=L.wireframe,M===oi?b.side=L.shadowSide!==null?L.shadowSide:L.side:b.side=L.shadowSide!==null?L.shadowSide:u[L.side],b.alphaMap=L.alphaMap,b.alphaTest=L.alphaTest,b.map=L.map,b.clipShadows=L.clipShadows,b.clippingPlanes=L.clippingPlanes,b.clipIntersection=L.clipIntersection,b.displacementMap=L.displacementMap,b.displacementScale=L.displacementScale,b.displacementBias=L.displacementBias,b.wireframeLinewidth=L.wireframeLinewidth,b.linewidth=L.linewidth,I.isPointLight===!0&&b.isMeshDistanceMaterial===!0){const k=i.properties.get(b);k.light=I}return b}function y(C,L,I,M,b){if(C.visible===!1)return;if(C.layers.test(L.layers)&&(C.isMesh||C.isLine||C.isPoints)&&(C.castShadow||C.receiveShadow&&b===oi)&&(!C.frustumCulled||n.intersectsObject(C))){C.modelViewMatrix.multiplyMatrices(I.matrixWorldInverse,C.matrixWorld);const H=t.update(C),Z=C.material;if(Array.isArray(Z)){const tt=H.groups;for(let O=0,et=tt.length;O<et;O++){const W=tt[O],lt=Z[W.materialIndex];if(lt&&lt.visible){const pt=w(C,lt,M,b);C.onBeforeShadow(i,C,L,I,H,pt,W),i.renderBufferDirect(I,null,H,pt,C,W),C.onAfterShadow(i,C,L,I,H,pt,W)}}}else if(Z.visible){const tt=w(C,Z,M,b);C.onBeforeShadow(i,C,L,I,H,tt,null),i.renderBufferDirect(I,null,H,tt,C,null),C.onAfterShadow(i,C,L,I,H,tt,null)}}const k=C.children;for(let H=0,Z=k.length;H<Z;H++)y(k[H],L,I,M,b)}function N(C){C.target.removeEventListener("dispose",N);for(const I in l){const M=l[I],b=C.target.uuid;b in M&&(M[b].dispose(),delete M[b])}}}const T0={[Ko]:Jo,[Zo]:ec,[Qo]:nc,[Rs]:tc,[Jo]:Ko,[ec]:Zo,[nc]:Qo,[tc]:Rs};function A0(i,t){function e(){let z=!1;const xt=new ye;let Q=null;const ot=new ye(0,0,0,0);return{setMask:function(Et){Q!==Et&&!z&&(i.colorMask(Et,Et,Et,Et),Q=Et)},setLocked:function(Et){z=Et},setClear:function(Et,bt,te,Pe,qe){qe===!0&&(Et*=Pe,bt*=Pe,te*=Pe),xt.set(Et,bt,te,Pe),ot.equals(xt)===!1&&(i.clearColor(Et,bt,te,Pe),ot.copy(xt))},reset:function(){z=!1,Q=null,ot.set(-1,0,0,0)}}}function n(){let z=!1,xt=!1,Q=null,ot=null,Et=null;return{setReversed:function(bt){if(xt!==bt){const te=t.get("EXT_clip_control");xt?te.clipControlEXT(te.LOWER_LEFT_EXT,te.ZERO_TO_ONE_EXT):te.clipControlEXT(te.LOWER_LEFT_EXT,te.NEGATIVE_ONE_TO_ONE_EXT);const Pe=Et;Et=null,this.setClear(Pe)}xt=bt},getReversed:function(){return xt},setTest:function(bt){bt?it(i.DEPTH_TEST):vt(i.DEPTH_TEST)},setMask:function(bt){Q!==bt&&!z&&(i.depthMask(bt),Q=bt)},setFunc:function(bt){if(xt&&(bt=T0[bt]),ot!==bt){switch(bt){case Ko:i.depthFunc(i.NEVER);break;case Jo:i.depthFunc(i.ALWAYS);break;case Zo:i.depthFunc(i.LESS);break;case Rs:i.depthFunc(i.LEQUAL);break;case Qo:i.depthFunc(i.EQUAL);break;case tc:i.depthFunc(i.GEQUAL);break;case ec:i.depthFunc(i.GREATER);break;case nc:i.depthFunc(i.NOTEQUAL);break;default:i.depthFunc(i.LEQUAL)}ot=bt}},setLocked:function(bt){z=bt},setClear:function(bt){Et!==bt&&(xt&&(bt=1-bt),i.clearDepth(bt),Et=bt)},reset:function(){z=!1,Q=null,ot=null,Et=null,xt=!1}}}function s(){let z=!1,xt=null,Q=null,ot=null,Et=null,bt=null,te=null,Pe=null,qe=null;return{setTest:function(se){z||(se?it(i.STENCIL_TEST):vt(i.STENCIL_TEST))},setMask:function(se){xt!==se&&!z&&(i.stencilMask(se),xt=se)},setFunc:function(se,cn,Nn){(Q!==se||ot!==cn||Et!==Nn)&&(i.stencilFunc(se,cn,Nn),Q=se,ot=cn,Et=Nn)},setOp:function(se,cn,Nn){(bt!==se||te!==cn||Pe!==Nn)&&(i.stencilOp(se,cn,Nn),bt=se,te=cn,Pe=Nn)},setLocked:function(se){z=se},setClear:function(se){qe!==se&&(i.clearStencil(se),qe=se)},reset:function(){z=!1,xt=null,Q=null,ot=null,Et=null,bt=null,te=null,Pe=null,qe=null}}}const r=new e,a=new n,o=new s,c=new WeakMap,l=new WeakMap;let h={},u={},d=new WeakMap,f=[],g=null,_=!1,m=null,p=null,P=null,w=null,y=null,N=null,C=null,L=new Jt(0,0,0),I=0,M=!1,b=null,F=null,k=null,H=null,Z=null;const tt=i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);let O=!1,et=0;const W=i.getParameter(i.VERSION);W.indexOf("WebGL")!==-1?(et=parseFloat(/^WebGL (\d)/.exec(W)[1]),O=et>=1):W.indexOf("OpenGL ES")!==-1&&(et=parseFloat(/^OpenGL ES (\d)/.exec(W)[1]),O=et>=2);let lt=null,pt={};const mt=i.getParameter(i.SCISSOR_BOX),Rt=i.getParameter(i.VIEWPORT),wt=new ye().fromArray(mt),q=new ye().fromArray(Rt);function J(z,xt,Q,ot){const Et=new Uint8Array(4),bt=i.createTexture();i.bindTexture(z,bt),i.texParameteri(z,i.TEXTURE_MIN_FILTER,i.NEAREST),i.texParameteri(z,i.TEXTURE_MAG_FILTER,i.NEAREST);for(let te=0;te<Q;te++)z===i.TEXTURE_3D||z===i.TEXTURE_2D_ARRAY?i.texImage3D(xt,0,i.RGBA,1,1,ot,0,i.RGBA,i.UNSIGNED_BYTE,Et):i.texImage2D(xt+te,0,i.RGBA,1,1,0,i.RGBA,i.UNSIGNED_BYTE,Et);return bt}const nt={};nt[i.TEXTURE_2D]=J(i.TEXTURE_2D,i.TEXTURE_2D,1),nt[i.TEXTURE_CUBE_MAP]=J(i.TEXTURE_CUBE_MAP,i.TEXTURE_CUBE_MAP_POSITIVE_X,6),nt[i.TEXTURE_2D_ARRAY]=J(i.TEXTURE_2D_ARRAY,i.TEXTURE_2D_ARRAY,1,1),nt[i.TEXTURE_3D]=J(i.TEXTURE_3D,i.TEXTURE_3D,1,1),r.setClear(0,0,0,1),a.setClear(1),o.setClear(0),it(i.DEPTH_TEST),a.setFunc(Rs),oe(!1),ce(pl),it(i.CULL_FACE),G(Pi);function it(z){h[z]!==!0&&(i.enable(z),h[z]=!0)}function vt(z){h[z]!==!1&&(i.disable(z),h[z]=!1)}function zt(z,xt){return u[z]!==xt?(i.bindFramebuffer(z,xt),u[z]=xt,z===i.DRAW_FRAMEBUFFER&&(u[i.FRAMEBUFFER]=xt),z===i.FRAMEBUFFER&&(u[i.DRAW_FRAMEBUFFER]=xt),!0):!1}function Qt(z,xt){let Q=f,ot=!1;if(z){Q=d.get(xt),Q===void 0&&(Q=[],d.set(xt,Q));const Et=z.textures;if(Q.length!==Et.length||Q[0]!==i.COLOR_ATTACHMENT0){for(let bt=0,te=Et.length;bt<te;bt++)Q[bt]=i.COLOR_ATTACHMENT0+bt;Q.length=Et.length,ot=!0}}else Q[0]!==i.BACK&&(Q[0]=i.BACK,ot=!0);ot&&i.drawBuffers(Q)}function Re(z){return g!==z?(i.useProgram(z),g=z,!0):!1}const ue={[qi]:i.FUNC_ADD,[Ad]:i.FUNC_SUBTRACT,[Cd]:i.FUNC_REVERSE_SUBTRACT};ue[Rd]=i.MIN,ue[Pd]=i.MAX;const Ie={[Ld]:i.ZERO,[Nd]:i.ONE,[Dd]:i.SRC_COLOR,[Yo]:i.SRC_ALPHA,[Bd]:i.SRC_ALPHA_SATURATE,[Od]:i.DST_COLOR,[Ud]:i.DST_ALPHA,[Id]:i.ONE_MINUS_SRC_COLOR,[$o]:i.ONE_MINUS_SRC_ALPHA,[kd]:i.ONE_MINUS_DST_COLOR,[Fd]:i.ONE_MINUS_DST_ALPHA,[zd]:i.CONSTANT_COLOR,[Vd]:i.ONE_MINUS_CONSTANT_COLOR,[Hd]:i.CONSTANT_ALPHA,[Gd]:i.ONE_MINUS_CONSTANT_ALPHA};function G(z,xt,Q,ot,Et,bt,te,Pe,qe,se){if(z===Pi){_===!0&&(vt(i.BLEND),_=!1);return}if(_===!1&&(it(i.BLEND),_=!0),z!==Td){if(z!==m||se!==M){if((p!==qi||y!==qi)&&(i.blendEquation(i.FUNC_ADD),p=qi,y=qi),se)switch(z){case Ss:i.blendFuncSeparate(i.ONE,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case ml:i.blendFunc(i.ONE,i.ONE);break;case gl:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case _l:i.blendFuncSeparate(i.ZERO,i.SRC_COLOR,i.ZERO,i.SRC_ALPHA);break;default:console.error("THREE.WebGLState: Invalid blending: ",z);break}else switch(z){case Ss:i.blendFuncSeparate(i.SRC_ALPHA,i.ONE_MINUS_SRC_ALPHA,i.ONE,i.ONE_MINUS_SRC_ALPHA);break;case ml:i.blendFunc(i.SRC_ALPHA,i.ONE);break;case gl:i.blendFuncSeparate(i.ZERO,i.ONE_MINUS_SRC_COLOR,i.ZERO,i.ONE);break;case _l:i.blendFunc(i.ZERO,i.SRC_COLOR);break;default:console.error("THREE.WebGLState: Invalid blending: ",z);break}P=null,w=null,N=null,C=null,L.set(0,0,0),I=0,m=z,M=se}return}Et=Et||xt,bt=bt||Q,te=te||ot,(xt!==p||Et!==y)&&(i.blendEquationSeparate(ue[xt],ue[Et]),p=xt,y=Et),(Q!==P||ot!==w||bt!==N||te!==C)&&(i.blendFuncSeparate(Ie[Q],Ie[ot],Ie[bt],Ie[te]),P=Q,w=ot,N=bt,C=te),(Pe.equals(L)===!1||qe!==I)&&(i.blendColor(Pe.r,Pe.g,Pe.b,qe),L.copy(Pe),I=qe),m=z,M=!1}function on(z,xt){z.side===dn?vt(i.CULL_FACE):it(i.CULL_FACE);let Q=z.side===fn;xt&&(Q=!Q),oe(Q),z.blending===Ss&&z.transparent===!1?G(Pi):G(z.blending,z.blendEquation,z.blendSrc,z.blendDst,z.blendEquationAlpha,z.blendSrcAlpha,z.blendDstAlpha,z.blendColor,z.blendAlpha,z.premultipliedAlpha),a.setFunc(z.depthFunc),a.setTest(z.depthTest),a.setMask(z.depthWrite),r.setMask(z.colorWrite);const ot=z.stencilWrite;o.setTest(ot),ot&&(o.setMask(z.stencilWriteMask),o.setFunc(z.stencilFunc,z.stencilRef,z.stencilFuncMask),o.setOp(z.stencilFail,z.stencilZFail,z.stencilZPass)),Ae(z.polygonOffset,z.polygonOffsetFactor,z.polygonOffsetUnits),z.alphaToCoverage===!0?it(i.SAMPLE_ALPHA_TO_COVERAGE):vt(i.SAMPLE_ALPHA_TO_COVERAGE)}function oe(z){b!==z&&(z?i.frontFace(i.CW):i.frontFace(i.CCW),b=z)}function ce(z){z!==Sd?(it(i.CULL_FACE),z!==F&&(z===pl?i.cullFace(i.BACK):z===Ed?i.cullFace(i.FRONT):i.cullFace(i.FRONT_AND_BACK))):vt(i.CULL_FACE),F=z}function Wt(z){z!==k&&(O&&i.lineWidth(z),k=z)}function Ae(z,xt,Q){z?(it(i.POLYGON_OFFSET_FILL),(H!==xt||Z!==Q)&&(i.polygonOffset(xt,Q),H=xt,Z=Q)):vt(i.POLYGON_OFFSET_FILL)}function Ht(z){z?it(i.SCISSOR_TEST):vt(i.SCISSOR_TEST)}function U(z){z===void 0&&(z=i.TEXTURE0+tt-1),lt!==z&&(i.activeTexture(z),lt=z)}function S(z,xt,Q){Q===void 0&&(lt===null?Q=i.TEXTURE0+tt-1:Q=lt);let ot=pt[Q];ot===void 0&&(ot={type:void 0,texture:void 0},pt[Q]=ot),(ot.type!==z||ot.texture!==xt)&&(lt!==Q&&(i.activeTexture(Q),lt=Q),i.bindTexture(z,xt||nt[z]),ot.type=z,ot.texture=xt)}function j(){const z=pt[lt];z!==void 0&&z.type!==void 0&&(i.bindTexture(z.type,null),z.type=void 0,z.texture=void 0)}function at(){try{i.compressedTexImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function ht(){try{i.compressedTexImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function rt(){try{i.texSubImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Ft(){try{i.texSubImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Mt(){try{i.compressedTexSubImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Ct(){try{i.compressedTexSubImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function de(){try{i.texStorage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function ft(){try{i.texStorage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Pt(){try{i.texImage2D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function Xt(){try{i.texImage3D.apply(i,arguments)}catch(z){console.error("THREE.WebGLState:",z)}}function $t(z){wt.equals(z)===!1&&(i.scissor(z.x,z.y,z.z,z.w),wt.copy(z))}function Lt(z){q.equals(z)===!1&&(i.viewport(z.x,z.y,z.z,z.w),q.copy(z))}function he(z,xt){let Q=l.get(xt);Q===void 0&&(Q=new WeakMap,l.set(xt,Q));let ot=Q.get(z);ot===void 0&&(ot=i.getUniformBlockIndex(xt,z.name),Q.set(z,ot))}function ne(z,xt){const ot=l.get(xt).get(z);c.get(xt)!==ot&&(i.uniformBlockBinding(xt,ot,z.__bindingPointIndex),c.set(xt,ot))}function Me(){i.disable(i.BLEND),i.disable(i.CULL_FACE),i.disable(i.DEPTH_TEST),i.disable(i.POLYGON_OFFSET_FILL),i.disable(i.SCISSOR_TEST),i.disable(i.STENCIL_TEST),i.disable(i.SAMPLE_ALPHA_TO_COVERAGE),i.blendEquation(i.FUNC_ADD),i.blendFunc(i.ONE,i.ZERO),i.blendFuncSeparate(i.ONE,i.ZERO,i.ONE,i.ZERO),i.blendColor(0,0,0,0),i.colorMask(!0,!0,!0,!0),i.clearColor(0,0,0,0),i.depthMask(!0),i.depthFunc(i.LESS),a.setReversed(!1),i.clearDepth(1),i.stencilMask(4294967295),i.stencilFunc(i.ALWAYS,0,4294967295),i.stencilOp(i.KEEP,i.KEEP,i.KEEP),i.clearStencil(0),i.cullFace(i.BACK),i.frontFace(i.CCW),i.polygonOffset(0,0),i.activeTexture(i.TEXTURE0),i.bindFramebuffer(i.FRAMEBUFFER,null),i.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),i.bindFramebuffer(i.READ_FRAMEBUFFER,null),i.useProgram(null),i.lineWidth(1),i.scissor(0,0,i.canvas.width,i.canvas.height),i.viewport(0,0,i.canvas.width,i.canvas.height),h={},lt=null,pt={},u={},d=new WeakMap,f=[],g=null,_=!1,m=null,p=null,P=null,w=null,y=null,N=null,C=null,L=new Jt(0,0,0),I=0,M=!1,b=null,F=null,k=null,H=null,Z=null,wt.set(0,0,i.canvas.width,i.canvas.height),q.set(0,0,i.canvas.width,i.canvas.height),r.reset(),a.reset(),o.reset()}return{buffers:{color:r,depth:a,stencil:o},enable:it,disable:vt,bindFramebuffer:zt,drawBuffers:Qt,useProgram:Re,setBlending:G,setMaterial:on,setFlipSided:oe,setCullFace:ce,setLineWidth:Wt,setPolygonOffset:Ae,setScissorTest:Ht,activeTexture:U,bindTexture:S,unbindTexture:j,compressedTexImage2D:at,compressedTexImage3D:ht,texImage2D:Pt,texImage3D:Xt,updateUBOMapping:he,uniformBlockBinding:ne,texStorage2D:de,texStorage3D:ft,texSubImage2D:rt,texSubImage3D:Ft,compressedTexSubImage2D:Mt,compressedTexSubImage3D:Ct,scissor:$t,viewport:Lt,reset:Me}}function gh(i,t,e,n){const s=C0(n);switch(e){case cu:return i*t;case hu:return i*t;case uu:return i*t*2;case du:return i*t/s.components*s.byteLength;case Gc:return i*t/s.components*s.byteLength;case fu:return i*t*2/s.components*s.byteLength;case Wc:return i*t*2/s.components*s.byteLength;case lu:return i*t*3/s.components*s.byteLength;case Pn:return i*t*4/s.components*s.byteLength;case Xc:return i*t*4/s.components*s.byteLength;case pa:case ma:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*8;case ga:case _a:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case oc:case lc:return Math.max(i,16)*Math.max(t,8)/4;case ac:case cc:return Math.max(i,8)*Math.max(t,8)/2;case hc:case uc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*8;case dc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case fc:return Math.floor((i+3)/4)*Math.floor((t+3)/4)*16;case pc:return Math.floor((i+4)/5)*Math.floor((t+3)/4)*16;case mc:return Math.floor((i+4)/5)*Math.floor((t+4)/5)*16;case gc:return Math.floor((i+5)/6)*Math.floor((t+4)/5)*16;case _c:return Math.floor((i+5)/6)*Math.floor((t+5)/6)*16;case vc:return Math.floor((i+7)/8)*Math.floor((t+4)/5)*16;case xc:return Math.floor((i+7)/8)*Math.floor((t+5)/6)*16;case yc:return Math.floor((i+7)/8)*Math.floor((t+7)/8)*16;case Mc:return Math.floor((i+9)/10)*Math.floor((t+4)/5)*16;case bc:return Math.floor((i+9)/10)*Math.floor((t+5)/6)*16;case Sc:return Math.floor((i+9)/10)*Math.floor((t+7)/8)*16;case Ec:return Math.floor((i+9)/10)*Math.floor((t+9)/10)*16;case wc:return Math.floor((i+11)/12)*Math.floor((t+9)/10)*16;case Tc:return Math.floor((i+11)/12)*Math.floor((t+11)/12)*16;case va:case Ac:case Cc:return Math.ceil(i/4)*Math.ceil(t/4)*16;case pu:case Rc:return Math.ceil(i/4)*Math.ceil(t/4)*8;case Pc:case Lc:return Math.ceil(i/4)*Math.ceil(t/4)*16}throw new Error(`Unable to determine texture byte length for ${e} format.`)}function C0(i){switch(i){case fi:case ru:return{byteLength:1,components:1};case pr:case au:case br:return{byteLength:2,components:1};case Vc:case Hc:return{byteLength:2,components:4};case Ki:case zc:case qn:return{byteLength:4,components:1};case ou:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${i}.`)}function R0(i,t,e,n,s,r,a){const o=t.has("WEBGL_multisampled_render_to_texture")?t.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),l=new At,h=new WeakMap;let u;const d=new WeakMap;let f=!1;try{f=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(U,S){return f?new OffscreenCanvas(U,S):mr("canvas")}function _(U,S,j){let at=1;const ht=Ht(U);if((ht.width>j||ht.height>j)&&(at=j/Math.max(ht.width,ht.height)),at<1)if(typeof HTMLImageElement<"u"&&U instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&U instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&U instanceof ImageBitmap||typeof VideoFrame<"u"&&U instanceof VideoFrame){const rt=Math.floor(at*ht.width),Ft=Math.floor(at*ht.height);u===void 0&&(u=g(rt,Ft));const Mt=S?g(rt,Ft):u;return Mt.width=rt,Mt.height=Ft,Mt.getContext("2d").drawImage(U,0,0,rt,Ft),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+ht.width+"x"+ht.height+") to ("+rt+"x"+Ft+")."),Mt}else return"data"in U&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+ht.width+"x"+ht.height+")."),U;return U}function m(U){return U.generateMipmaps}function p(U){i.generateMipmap(U)}function P(U){return U.isWebGLCubeRenderTarget?i.TEXTURE_CUBE_MAP:U.isWebGL3DRenderTarget?i.TEXTURE_3D:U.isWebGLArrayRenderTarget||U.isCompressedArrayTexture?i.TEXTURE_2D_ARRAY:i.TEXTURE_2D}function w(U,S,j,at,ht=!1){if(U!==null){if(i[U]!==void 0)return i[U];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+U+"'")}let rt=S;if(S===i.RED&&(j===i.FLOAT&&(rt=i.R32F),j===i.HALF_FLOAT&&(rt=i.R16F),j===i.UNSIGNED_BYTE&&(rt=i.R8)),S===i.RED_INTEGER&&(j===i.UNSIGNED_BYTE&&(rt=i.R8UI),j===i.UNSIGNED_SHORT&&(rt=i.R16UI),j===i.UNSIGNED_INT&&(rt=i.R32UI),j===i.BYTE&&(rt=i.R8I),j===i.SHORT&&(rt=i.R16I),j===i.INT&&(rt=i.R32I)),S===i.RG&&(j===i.FLOAT&&(rt=i.RG32F),j===i.HALF_FLOAT&&(rt=i.RG16F),j===i.UNSIGNED_BYTE&&(rt=i.RG8)),S===i.RG_INTEGER&&(j===i.UNSIGNED_BYTE&&(rt=i.RG8UI),j===i.UNSIGNED_SHORT&&(rt=i.RG16UI),j===i.UNSIGNED_INT&&(rt=i.RG32UI),j===i.BYTE&&(rt=i.RG8I),j===i.SHORT&&(rt=i.RG16I),j===i.INT&&(rt=i.RG32I)),S===i.RGB_INTEGER&&(j===i.UNSIGNED_BYTE&&(rt=i.RGB8UI),j===i.UNSIGNED_SHORT&&(rt=i.RGB16UI),j===i.UNSIGNED_INT&&(rt=i.RGB32UI),j===i.BYTE&&(rt=i.RGB8I),j===i.SHORT&&(rt=i.RGB16I),j===i.INT&&(rt=i.RGB32I)),S===i.RGBA_INTEGER&&(j===i.UNSIGNED_BYTE&&(rt=i.RGBA8UI),j===i.UNSIGNED_SHORT&&(rt=i.RGBA16UI),j===i.UNSIGNED_INT&&(rt=i.RGBA32UI),j===i.BYTE&&(rt=i.RGBA8I),j===i.SHORT&&(rt=i.RGBA16I),j===i.INT&&(rt=i.RGBA32I)),S===i.RGB&&j===i.UNSIGNED_INT_5_9_9_9_REV&&(rt=i.RGB9_E5),S===i.RGBA){const Ft=ht?Va:le.getTransfer(at);j===i.FLOAT&&(rt=i.RGBA32F),j===i.HALF_FLOAT&&(rt=i.RGBA16F),j===i.UNSIGNED_BYTE&&(rt=Ft===we?i.SRGB8_ALPHA8:i.RGBA8),j===i.UNSIGNED_SHORT_4_4_4_4&&(rt=i.RGBA4),j===i.UNSIGNED_SHORT_5_5_5_1&&(rt=i.RGB5_A1)}return(rt===i.R16F||rt===i.R32F||rt===i.RG16F||rt===i.RG32F||rt===i.RGBA16F||rt===i.RGBA32F)&&t.get("EXT_color_buffer_float"),rt}function y(U,S){let j;return U?S===null||S===Ki||S===Ns?j=i.DEPTH24_STENCIL8:S===qn?j=i.DEPTH32F_STENCIL8:S===pr&&(j=i.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):S===null||S===Ki||S===Ns?j=i.DEPTH_COMPONENT24:S===qn?j=i.DEPTH_COMPONENT32F:S===pr&&(j=i.DEPTH_COMPONENT16),j}function N(U,S){return m(U)===!0||U.isFramebufferTexture&&U.minFilter!==Mn&&U.minFilter!==xn?Math.log2(Math.max(S.width,S.height))+1:U.mipmaps!==void 0&&U.mipmaps.length>0?U.mipmaps.length:U.isCompressedTexture&&Array.isArray(U.image)?S.mipmaps.length:1}function C(U){const S=U.target;S.removeEventListener("dispose",C),I(S),S.isVideoTexture&&h.delete(S)}function L(U){const S=U.target;S.removeEventListener("dispose",L),b(S)}function I(U){const S=n.get(U);if(S.__webglInit===void 0)return;const j=U.source,at=d.get(j);if(at){const ht=at[S.__cacheKey];ht.usedTimes--,ht.usedTimes===0&&M(U),Object.keys(at).length===0&&d.delete(j)}n.remove(U)}function M(U){const S=n.get(U);i.deleteTexture(S.__webglTexture);const j=U.source,at=d.get(j);delete at[S.__cacheKey],a.memory.textures--}function b(U){const S=n.get(U);if(U.depthTexture&&(U.depthTexture.dispose(),n.remove(U.depthTexture)),U.isWebGLCubeRenderTarget)for(let at=0;at<6;at++){if(Array.isArray(S.__webglFramebuffer[at]))for(let ht=0;ht<S.__webglFramebuffer[at].length;ht++)i.deleteFramebuffer(S.__webglFramebuffer[at][ht]);else i.deleteFramebuffer(S.__webglFramebuffer[at]);S.__webglDepthbuffer&&i.deleteRenderbuffer(S.__webglDepthbuffer[at])}else{if(Array.isArray(S.__webglFramebuffer))for(let at=0;at<S.__webglFramebuffer.length;at++)i.deleteFramebuffer(S.__webglFramebuffer[at]);else i.deleteFramebuffer(S.__webglFramebuffer);if(S.__webglDepthbuffer&&i.deleteRenderbuffer(S.__webglDepthbuffer),S.__webglMultisampledFramebuffer&&i.deleteFramebuffer(S.__webglMultisampledFramebuffer),S.__webglColorRenderbuffer)for(let at=0;at<S.__webglColorRenderbuffer.length;at++)S.__webglColorRenderbuffer[at]&&i.deleteRenderbuffer(S.__webglColorRenderbuffer[at]);S.__webglDepthRenderbuffer&&i.deleteRenderbuffer(S.__webglDepthRenderbuffer)}const j=U.textures;for(let at=0,ht=j.length;at<ht;at++){const rt=n.get(j[at]);rt.__webglTexture&&(i.deleteTexture(rt.__webglTexture),a.memory.textures--),n.remove(j[at])}n.remove(U)}let F=0;function k(){F=0}function H(){const U=F;return U>=s.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+U+" texture units while this GPU supports only "+s.maxTextures),F+=1,U}function Z(U){const S=[];return S.push(U.wrapS),S.push(U.wrapT),S.push(U.wrapR||0),S.push(U.magFilter),S.push(U.minFilter),S.push(U.anisotropy),S.push(U.internalFormat),S.push(U.format),S.push(U.type),S.push(U.generateMipmaps),S.push(U.premultiplyAlpha),S.push(U.flipY),S.push(U.unpackAlignment),S.push(U.colorSpace),S.join()}function tt(U,S){const j=n.get(U);if(U.isVideoTexture&&Wt(U),U.isRenderTargetTexture===!1&&U.version>0&&j.__version!==U.version){const at=U.image;if(at===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(at.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{q(j,U,S);return}}e.bindTexture(i.TEXTURE_2D,j.__webglTexture,i.TEXTURE0+S)}function O(U,S){const j=n.get(U);if(U.version>0&&j.__version!==U.version){q(j,U,S);return}e.bindTexture(i.TEXTURE_2D_ARRAY,j.__webglTexture,i.TEXTURE0+S)}function et(U,S){const j=n.get(U);if(U.version>0&&j.__version!==U.version){q(j,U,S);return}e.bindTexture(i.TEXTURE_3D,j.__webglTexture,i.TEXTURE0+S)}function W(U,S){const j=n.get(U);if(U.version>0&&j.__version!==U.version){J(j,U,S);return}e.bindTexture(i.TEXTURE_CUBE_MAP,j.__webglTexture,i.TEXTURE0+S)}const lt={[Yi]:i.REPEAT,[Bn]:i.CLAMP_TO_EDGE,[rc]:i.MIRRORED_REPEAT},pt={[Mn]:i.NEAREST,[Qd]:i.NEAREST_MIPMAP_NEAREST,[Dr]:i.NEAREST_MIPMAP_LINEAR,[xn]:i.LINEAR,[no]:i.LINEAR_MIPMAP_NEAREST,[li]:i.LINEAR_MIPMAP_LINEAR},mt={[rf]:i.NEVER,[uf]:i.ALWAYS,[af]:i.LESS,[mu]:i.LEQUAL,[of]:i.EQUAL,[hf]:i.GEQUAL,[cf]:i.GREATER,[lf]:i.NOTEQUAL};function Rt(U,S){if(S.type===qn&&t.has("OES_texture_float_linear")===!1&&(S.magFilter===xn||S.magFilter===no||S.magFilter===Dr||S.magFilter===li||S.minFilter===xn||S.minFilter===no||S.minFilter===Dr||S.minFilter===li)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),i.texParameteri(U,i.TEXTURE_WRAP_S,lt[S.wrapS]),i.texParameteri(U,i.TEXTURE_WRAP_T,lt[S.wrapT]),(U===i.TEXTURE_3D||U===i.TEXTURE_2D_ARRAY)&&i.texParameteri(U,i.TEXTURE_WRAP_R,lt[S.wrapR]),i.texParameteri(U,i.TEXTURE_MAG_FILTER,pt[S.magFilter]),i.texParameteri(U,i.TEXTURE_MIN_FILTER,pt[S.minFilter]),S.compareFunction&&(i.texParameteri(U,i.TEXTURE_COMPARE_MODE,i.COMPARE_REF_TO_TEXTURE),i.texParameteri(U,i.TEXTURE_COMPARE_FUNC,mt[S.compareFunction])),t.has("EXT_texture_filter_anisotropic")===!0){if(S.magFilter===Mn||S.minFilter!==Dr&&S.minFilter!==li||S.type===qn&&t.has("OES_texture_float_linear")===!1)return;if(S.anisotropy>1||n.get(S).__currentAnisotropy){const j=t.get("EXT_texture_filter_anisotropic");i.texParameterf(U,j.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(S.anisotropy,s.getMaxAnisotropy())),n.get(S).__currentAnisotropy=S.anisotropy}}}function wt(U,S){let j=!1;U.__webglInit===void 0&&(U.__webglInit=!0,S.addEventListener("dispose",C));const at=S.source;let ht=d.get(at);ht===void 0&&(ht={},d.set(at,ht));const rt=Z(S);if(rt!==U.__cacheKey){ht[rt]===void 0&&(ht[rt]={texture:i.createTexture(),usedTimes:0},a.memory.textures++,j=!0),ht[rt].usedTimes++;const Ft=ht[U.__cacheKey];Ft!==void 0&&(ht[U.__cacheKey].usedTimes--,Ft.usedTimes===0&&M(S)),U.__cacheKey=rt,U.__webglTexture=ht[rt].texture}return j}function q(U,S,j){let at=i.TEXTURE_2D;(S.isDataArrayTexture||S.isCompressedArrayTexture)&&(at=i.TEXTURE_2D_ARRAY),S.isData3DTexture&&(at=i.TEXTURE_3D);const ht=wt(U,S),rt=S.source;e.bindTexture(at,U.__webglTexture,i.TEXTURE0+j);const Ft=n.get(rt);if(rt.version!==Ft.__version||ht===!0){e.activeTexture(i.TEXTURE0+j);const Mt=le.getPrimaries(le.workingColorSpace),Ct=S.colorSpace===Ci?null:le.getPrimaries(S.colorSpace),de=S.colorSpace===Ci||Mt===Ct?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,S.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,S.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,S.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,de);let ft=_(S.image,!1,s.maxTextureSize);ft=Ae(S,ft);const Pt=r.convert(S.format,S.colorSpace),Xt=r.convert(S.type);let $t=w(S.internalFormat,Pt,Xt,S.colorSpace,S.isVideoTexture);Rt(at,S);let Lt;const he=S.mipmaps,ne=S.isVideoTexture!==!0,Me=Ft.__version===void 0||ht===!0,z=rt.dataReady,xt=N(S,ft);if(S.isDepthTexture)$t=y(S.format===Ds,S.type),Me&&(ne?e.texStorage2D(i.TEXTURE_2D,1,$t,ft.width,ft.height):e.texImage2D(i.TEXTURE_2D,0,$t,ft.width,ft.height,0,Pt,Xt,null));else if(S.isDataTexture)if(he.length>0){ne&&Me&&e.texStorage2D(i.TEXTURE_2D,xt,$t,he[0].width,he[0].height);for(let Q=0,ot=he.length;Q<ot;Q++)Lt=he[Q],ne?z&&e.texSubImage2D(i.TEXTURE_2D,Q,0,0,Lt.width,Lt.height,Pt,Xt,Lt.data):e.texImage2D(i.TEXTURE_2D,Q,$t,Lt.width,Lt.height,0,Pt,Xt,Lt.data);S.generateMipmaps=!1}else ne?(Me&&e.texStorage2D(i.TEXTURE_2D,xt,$t,ft.width,ft.height),z&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,ft.width,ft.height,Pt,Xt,ft.data)):e.texImage2D(i.TEXTURE_2D,0,$t,ft.width,ft.height,0,Pt,Xt,ft.data);else if(S.isCompressedTexture)if(S.isCompressedArrayTexture){ne&&Me&&e.texStorage3D(i.TEXTURE_2D_ARRAY,xt,$t,he[0].width,he[0].height,ft.depth);for(let Q=0,ot=he.length;Q<ot;Q++)if(Lt=he[Q],S.format!==Pn)if(Pt!==null)if(ne){if(z)if(S.layerUpdates.size>0){const Et=gh(Lt.width,Lt.height,S.format,S.type);for(const bt of S.layerUpdates){const te=Lt.data.subarray(bt*Et/Lt.data.BYTES_PER_ELEMENT,(bt+1)*Et/Lt.data.BYTES_PER_ELEMENT);e.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,Q,0,0,bt,Lt.width,Lt.height,1,Pt,te)}S.clearLayerUpdates()}else e.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY,Q,0,0,0,Lt.width,Lt.height,ft.depth,Pt,Lt.data)}else e.compressedTexImage3D(i.TEXTURE_2D_ARRAY,Q,$t,Lt.width,Lt.height,ft.depth,0,Lt.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else ne?z&&e.texSubImage3D(i.TEXTURE_2D_ARRAY,Q,0,0,0,Lt.width,Lt.height,ft.depth,Pt,Xt,Lt.data):e.texImage3D(i.TEXTURE_2D_ARRAY,Q,$t,Lt.width,Lt.height,ft.depth,0,Pt,Xt,Lt.data)}else{ne&&Me&&e.texStorage2D(i.TEXTURE_2D,xt,$t,he[0].width,he[0].height);for(let Q=0,ot=he.length;Q<ot;Q++)Lt=he[Q],S.format!==Pn?Pt!==null?ne?z&&e.compressedTexSubImage2D(i.TEXTURE_2D,Q,0,0,Lt.width,Lt.height,Pt,Lt.data):e.compressedTexImage2D(i.TEXTURE_2D,Q,$t,Lt.width,Lt.height,0,Lt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):ne?z&&e.texSubImage2D(i.TEXTURE_2D,Q,0,0,Lt.width,Lt.height,Pt,Xt,Lt.data):e.texImage2D(i.TEXTURE_2D,Q,$t,Lt.width,Lt.height,0,Pt,Xt,Lt.data)}else if(S.isDataArrayTexture)if(ne){if(Me&&e.texStorage3D(i.TEXTURE_2D_ARRAY,xt,$t,ft.width,ft.height,ft.depth),z)if(S.layerUpdates.size>0){const Q=gh(ft.width,ft.height,S.format,S.type);for(const ot of S.layerUpdates){const Et=ft.data.subarray(ot*Q/ft.data.BYTES_PER_ELEMENT,(ot+1)*Q/ft.data.BYTES_PER_ELEMENT);e.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,ot,ft.width,ft.height,1,Pt,Xt,Et)}S.clearLayerUpdates()}else e.texSubImage3D(i.TEXTURE_2D_ARRAY,0,0,0,0,ft.width,ft.height,ft.depth,Pt,Xt,ft.data)}else e.texImage3D(i.TEXTURE_2D_ARRAY,0,$t,ft.width,ft.height,ft.depth,0,Pt,Xt,ft.data);else if(S.isData3DTexture)ne?(Me&&e.texStorage3D(i.TEXTURE_3D,xt,$t,ft.width,ft.height,ft.depth),z&&e.texSubImage3D(i.TEXTURE_3D,0,0,0,0,ft.width,ft.height,ft.depth,Pt,Xt,ft.data)):e.texImage3D(i.TEXTURE_3D,0,$t,ft.width,ft.height,ft.depth,0,Pt,Xt,ft.data);else if(S.isFramebufferTexture){if(Me)if(ne)e.texStorage2D(i.TEXTURE_2D,xt,$t,ft.width,ft.height);else{let Q=ft.width,ot=ft.height;for(let Et=0;Et<xt;Et++)e.texImage2D(i.TEXTURE_2D,Et,$t,Q,ot,0,Pt,Xt,null),Q>>=1,ot>>=1}}else if(he.length>0){if(ne&&Me){const Q=Ht(he[0]);e.texStorage2D(i.TEXTURE_2D,xt,$t,Q.width,Q.height)}for(let Q=0,ot=he.length;Q<ot;Q++)Lt=he[Q],ne?z&&e.texSubImage2D(i.TEXTURE_2D,Q,0,0,Pt,Xt,Lt):e.texImage2D(i.TEXTURE_2D,Q,$t,Pt,Xt,Lt);S.generateMipmaps=!1}else if(ne){if(Me){const Q=Ht(ft);e.texStorage2D(i.TEXTURE_2D,xt,$t,Q.width,Q.height)}z&&e.texSubImage2D(i.TEXTURE_2D,0,0,0,Pt,Xt,ft)}else e.texImage2D(i.TEXTURE_2D,0,$t,Pt,Xt,ft);m(S)&&p(at),Ft.__version=rt.version,S.onUpdate&&S.onUpdate(S)}U.__version=S.version}function J(U,S,j){if(S.image.length!==6)return;const at=wt(U,S),ht=S.source;e.bindTexture(i.TEXTURE_CUBE_MAP,U.__webglTexture,i.TEXTURE0+j);const rt=n.get(ht);if(ht.version!==rt.__version||at===!0){e.activeTexture(i.TEXTURE0+j);const Ft=le.getPrimaries(le.workingColorSpace),Mt=S.colorSpace===Ci?null:le.getPrimaries(S.colorSpace),Ct=S.colorSpace===Ci||Ft===Mt?i.NONE:i.BROWSER_DEFAULT_WEBGL;i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL,S.flipY),i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL,S.premultiplyAlpha),i.pixelStorei(i.UNPACK_ALIGNMENT,S.unpackAlignment),i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL,Ct);const de=S.isCompressedTexture||S.image[0].isCompressedTexture,ft=S.image[0]&&S.image[0].isDataTexture,Pt=[];for(let ot=0;ot<6;ot++)!de&&!ft?Pt[ot]=_(S.image[ot],!0,s.maxCubemapSize):Pt[ot]=ft?S.image[ot].image:S.image[ot],Pt[ot]=Ae(S,Pt[ot]);const Xt=Pt[0],$t=r.convert(S.format,S.colorSpace),Lt=r.convert(S.type),he=w(S.internalFormat,$t,Lt,S.colorSpace),ne=S.isVideoTexture!==!0,Me=rt.__version===void 0||at===!0,z=ht.dataReady;let xt=N(S,Xt);Rt(i.TEXTURE_CUBE_MAP,S);let Q;if(de){ne&&Me&&e.texStorage2D(i.TEXTURE_CUBE_MAP,xt,he,Xt.width,Xt.height);for(let ot=0;ot<6;ot++){Q=Pt[ot].mipmaps;for(let Et=0;Et<Q.length;Et++){const bt=Q[Et];S.format!==Pn?$t!==null?ne?z&&e.compressedTexSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et,0,0,bt.width,bt.height,$t,bt.data):e.compressedTexImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et,he,bt.width,bt.height,0,bt.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):ne?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et,0,0,bt.width,bt.height,$t,Lt,bt.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et,he,bt.width,bt.height,0,$t,Lt,bt.data)}}}else{if(Q=S.mipmaps,ne&&Me){Q.length>0&&xt++;const ot=Ht(Pt[0]);e.texStorage2D(i.TEXTURE_CUBE_MAP,xt,he,ot.width,ot.height)}for(let ot=0;ot<6;ot++)if(ft){ne?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,0,0,0,Pt[ot].width,Pt[ot].height,$t,Lt,Pt[ot].data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,0,he,Pt[ot].width,Pt[ot].height,0,$t,Lt,Pt[ot].data);for(let Et=0;Et<Q.length;Et++){const te=Q[Et].image[ot].image;ne?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et+1,0,0,te.width,te.height,$t,Lt,te.data):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et+1,he,te.width,te.height,0,$t,Lt,te.data)}}else{ne?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,0,0,0,$t,Lt,Pt[ot]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,0,he,$t,Lt,Pt[ot]);for(let Et=0;Et<Q.length;Et++){const bt=Q[Et];ne?z&&e.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et+1,0,0,$t,Lt,bt.image[ot]):e.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X+ot,Et+1,he,$t,Lt,bt.image[ot])}}}m(S)&&p(i.TEXTURE_CUBE_MAP),rt.__version=ht.version,S.onUpdate&&S.onUpdate(S)}U.__version=S.version}function nt(U,S,j,at,ht,rt){const Ft=r.convert(j.format,j.colorSpace),Mt=r.convert(j.type),Ct=w(j.internalFormat,Ft,Mt,j.colorSpace),de=n.get(S),ft=n.get(j);if(ft.__renderTarget=S,!de.__hasExternalTextures){const Pt=Math.max(1,S.width>>rt),Xt=Math.max(1,S.height>>rt);ht===i.TEXTURE_3D||ht===i.TEXTURE_2D_ARRAY?e.texImage3D(ht,rt,Ct,Pt,Xt,S.depth,0,Ft,Mt,null):e.texImage2D(ht,rt,Ct,Pt,Xt,0,Ft,Mt,null)}e.bindFramebuffer(i.FRAMEBUFFER,U),ce(S)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,at,ht,ft.__webglTexture,0,oe(S)):(ht===i.TEXTURE_2D||ht>=i.TEXTURE_CUBE_MAP_POSITIVE_X&&ht<=i.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&i.framebufferTexture2D(i.FRAMEBUFFER,at,ht,ft.__webglTexture,rt),e.bindFramebuffer(i.FRAMEBUFFER,null)}function it(U,S,j){if(i.bindRenderbuffer(i.RENDERBUFFER,U),S.depthBuffer){const at=S.depthTexture,ht=at&&at.isDepthTexture?at.type:null,rt=y(S.stencilBuffer,ht),Ft=S.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,Mt=oe(S);ce(S)?o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,Mt,rt,S.width,S.height):j?i.renderbufferStorageMultisample(i.RENDERBUFFER,Mt,rt,S.width,S.height):i.renderbufferStorage(i.RENDERBUFFER,rt,S.width,S.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,Ft,i.RENDERBUFFER,U)}else{const at=S.textures;for(let ht=0;ht<at.length;ht++){const rt=at[ht],Ft=r.convert(rt.format,rt.colorSpace),Mt=r.convert(rt.type),Ct=w(rt.internalFormat,Ft,Mt,rt.colorSpace),de=oe(S);j&&ce(S)===!1?i.renderbufferStorageMultisample(i.RENDERBUFFER,de,Ct,S.width,S.height):ce(S)?o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER,de,Ct,S.width,S.height):i.renderbufferStorage(i.RENDERBUFFER,Ct,S.width,S.height)}}i.bindRenderbuffer(i.RENDERBUFFER,null)}function vt(U,S){if(S&&S.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(e.bindFramebuffer(i.FRAMEBUFFER,U),!(S.depthTexture&&S.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");const at=n.get(S.depthTexture);at.__renderTarget=S,(!at.__webglTexture||S.depthTexture.image.width!==S.width||S.depthTexture.image.height!==S.height)&&(S.depthTexture.image.width=S.width,S.depthTexture.image.height=S.height,S.depthTexture.needsUpdate=!0),tt(S.depthTexture,0);const ht=at.__webglTexture,rt=oe(S);if(S.depthTexture.format===Es)ce(S)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,ht,0,rt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_ATTACHMENT,i.TEXTURE_2D,ht,0);else if(S.depthTexture.format===Ds)ce(S)?o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,ht,0,rt):i.framebufferTexture2D(i.FRAMEBUFFER,i.DEPTH_STENCIL_ATTACHMENT,i.TEXTURE_2D,ht,0);else throw new Error("Unknown depthTexture format")}function zt(U){const S=n.get(U),j=U.isWebGLCubeRenderTarget===!0;if(S.__boundDepthTexture!==U.depthTexture){const at=U.depthTexture;if(S.__depthDisposeCallback&&S.__depthDisposeCallback(),at){const ht=()=>{delete S.__boundDepthTexture,delete S.__depthDisposeCallback,at.removeEventListener("dispose",ht)};at.addEventListener("dispose",ht),S.__depthDisposeCallback=ht}S.__boundDepthTexture=at}if(U.depthTexture&&!S.__autoAllocateDepthBuffer){if(j)throw new Error("target.depthTexture not supported in Cube render targets");vt(S.__webglFramebuffer,U)}else if(j){S.__webglDepthbuffer=[];for(let at=0;at<6;at++)if(e.bindFramebuffer(i.FRAMEBUFFER,S.__webglFramebuffer[at]),S.__webglDepthbuffer[at]===void 0)S.__webglDepthbuffer[at]=i.createRenderbuffer(),it(S.__webglDepthbuffer[at],U,!1);else{const ht=U.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,rt=S.__webglDepthbuffer[at];i.bindRenderbuffer(i.RENDERBUFFER,rt),i.framebufferRenderbuffer(i.FRAMEBUFFER,ht,i.RENDERBUFFER,rt)}}else if(e.bindFramebuffer(i.FRAMEBUFFER,S.__webglFramebuffer),S.__webglDepthbuffer===void 0)S.__webglDepthbuffer=i.createRenderbuffer(),it(S.__webglDepthbuffer,U,!1);else{const at=U.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,ht=S.__webglDepthbuffer;i.bindRenderbuffer(i.RENDERBUFFER,ht),i.framebufferRenderbuffer(i.FRAMEBUFFER,at,i.RENDERBUFFER,ht)}e.bindFramebuffer(i.FRAMEBUFFER,null)}function Qt(U,S,j){const at=n.get(U);S!==void 0&&nt(at.__webglFramebuffer,U,U.texture,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,0),j!==void 0&&zt(U)}function Re(U){const S=U.texture,j=n.get(U),at=n.get(S);U.addEventListener("dispose",L);const ht=U.textures,rt=U.isWebGLCubeRenderTarget===!0,Ft=ht.length>1;if(Ft||(at.__webglTexture===void 0&&(at.__webglTexture=i.createTexture()),at.__version=S.version,a.memory.textures++),rt){j.__webglFramebuffer=[];for(let Mt=0;Mt<6;Mt++)if(S.mipmaps&&S.mipmaps.length>0){j.__webglFramebuffer[Mt]=[];for(let Ct=0;Ct<S.mipmaps.length;Ct++)j.__webglFramebuffer[Mt][Ct]=i.createFramebuffer()}else j.__webglFramebuffer[Mt]=i.createFramebuffer()}else{if(S.mipmaps&&S.mipmaps.length>0){j.__webglFramebuffer=[];for(let Mt=0;Mt<S.mipmaps.length;Mt++)j.__webglFramebuffer[Mt]=i.createFramebuffer()}else j.__webglFramebuffer=i.createFramebuffer();if(Ft)for(let Mt=0,Ct=ht.length;Mt<Ct;Mt++){const de=n.get(ht[Mt]);de.__webglTexture===void 0&&(de.__webglTexture=i.createTexture(),a.memory.textures++)}if(U.samples>0&&ce(U)===!1){j.__webglMultisampledFramebuffer=i.createFramebuffer(),j.__webglColorRenderbuffer=[],e.bindFramebuffer(i.FRAMEBUFFER,j.__webglMultisampledFramebuffer);for(let Mt=0;Mt<ht.length;Mt++){const Ct=ht[Mt];j.__webglColorRenderbuffer[Mt]=i.createRenderbuffer(),i.bindRenderbuffer(i.RENDERBUFFER,j.__webglColorRenderbuffer[Mt]);const de=r.convert(Ct.format,Ct.colorSpace),ft=r.convert(Ct.type),Pt=w(Ct.internalFormat,de,ft,Ct.colorSpace,U.isXRRenderTarget===!0),Xt=oe(U);i.renderbufferStorageMultisample(i.RENDERBUFFER,Xt,Pt,U.width,U.height),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Mt,i.RENDERBUFFER,j.__webglColorRenderbuffer[Mt])}i.bindRenderbuffer(i.RENDERBUFFER,null),U.depthBuffer&&(j.__webglDepthRenderbuffer=i.createRenderbuffer(),it(j.__webglDepthRenderbuffer,U,!0)),e.bindFramebuffer(i.FRAMEBUFFER,null)}}if(rt){e.bindTexture(i.TEXTURE_CUBE_MAP,at.__webglTexture),Rt(i.TEXTURE_CUBE_MAP,S);for(let Mt=0;Mt<6;Mt++)if(S.mipmaps&&S.mipmaps.length>0)for(let Ct=0;Ct<S.mipmaps.length;Ct++)nt(j.__webglFramebuffer[Mt][Ct],U,S,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+Mt,Ct);else nt(j.__webglFramebuffer[Mt],U,S,i.COLOR_ATTACHMENT0,i.TEXTURE_CUBE_MAP_POSITIVE_X+Mt,0);m(S)&&p(i.TEXTURE_CUBE_MAP),e.unbindTexture()}else if(Ft){for(let Mt=0,Ct=ht.length;Mt<Ct;Mt++){const de=ht[Mt],ft=n.get(de);e.bindTexture(i.TEXTURE_2D,ft.__webglTexture),Rt(i.TEXTURE_2D,de),nt(j.__webglFramebuffer,U,de,i.COLOR_ATTACHMENT0+Mt,i.TEXTURE_2D,0),m(de)&&p(i.TEXTURE_2D)}e.unbindTexture()}else{let Mt=i.TEXTURE_2D;if((U.isWebGL3DRenderTarget||U.isWebGLArrayRenderTarget)&&(Mt=U.isWebGL3DRenderTarget?i.TEXTURE_3D:i.TEXTURE_2D_ARRAY),e.bindTexture(Mt,at.__webglTexture),Rt(Mt,S),S.mipmaps&&S.mipmaps.length>0)for(let Ct=0;Ct<S.mipmaps.length;Ct++)nt(j.__webglFramebuffer[Ct],U,S,i.COLOR_ATTACHMENT0,Mt,Ct);else nt(j.__webglFramebuffer,U,S,i.COLOR_ATTACHMENT0,Mt,0);m(S)&&p(Mt),e.unbindTexture()}U.depthBuffer&&zt(U)}function ue(U){const S=U.textures;for(let j=0,at=S.length;j<at;j++){const ht=S[j];if(m(ht)){const rt=P(U),Ft=n.get(ht).__webglTexture;e.bindTexture(rt,Ft),p(rt),e.unbindTexture()}}}const Ie=[],G=[];function on(U){if(U.samples>0){if(ce(U)===!1){const S=U.textures,j=U.width,at=U.height;let ht=i.COLOR_BUFFER_BIT;const rt=U.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT,Ft=n.get(U),Mt=S.length>1;if(Mt)for(let Ct=0;Ct<S.length;Ct++)e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.RENDERBUFFER,null),e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.TEXTURE_2D,null,0);e.bindFramebuffer(i.READ_FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,Ft.__webglFramebuffer);for(let Ct=0;Ct<S.length;Ct++){if(U.resolveDepthBuffer&&(U.depthBuffer&&(ht|=i.DEPTH_BUFFER_BIT),U.stencilBuffer&&U.resolveStencilBuffer&&(ht|=i.STENCIL_BUFFER_BIT)),Mt){i.framebufferRenderbuffer(i.READ_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.RENDERBUFFER,Ft.__webglColorRenderbuffer[Ct]);const de=n.get(S[Ct]).__webglTexture;i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0,i.TEXTURE_2D,de,0)}i.blitFramebuffer(0,0,j,at,0,0,j,at,ht,i.NEAREST),c===!0&&(Ie.length=0,G.length=0,Ie.push(i.COLOR_ATTACHMENT0+Ct),U.depthBuffer&&U.resolveDepthBuffer===!1&&(Ie.push(rt),G.push(rt),i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,G)),i.invalidateFramebuffer(i.READ_FRAMEBUFFER,Ie))}if(e.bindFramebuffer(i.READ_FRAMEBUFFER,null),e.bindFramebuffer(i.DRAW_FRAMEBUFFER,null),Mt)for(let Ct=0;Ct<S.length;Ct++){e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglMultisampledFramebuffer),i.framebufferRenderbuffer(i.FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.RENDERBUFFER,Ft.__webglColorRenderbuffer[Ct]);const de=n.get(S[Ct]).__webglTexture;e.bindFramebuffer(i.FRAMEBUFFER,Ft.__webglFramebuffer),i.framebufferTexture2D(i.DRAW_FRAMEBUFFER,i.COLOR_ATTACHMENT0+Ct,i.TEXTURE_2D,de,0)}e.bindFramebuffer(i.DRAW_FRAMEBUFFER,Ft.__webglMultisampledFramebuffer)}else if(U.depthBuffer&&U.resolveDepthBuffer===!1&&c){const S=U.stencilBuffer?i.DEPTH_STENCIL_ATTACHMENT:i.DEPTH_ATTACHMENT;i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER,[S])}}}function oe(U){return Math.min(s.maxSamples,U.samples)}function ce(U){const S=n.get(U);return U.samples>0&&t.has("WEBGL_multisampled_render_to_texture")===!0&&S.__useRenderToTexture!==!1}function Wt(U){const S=a.render.frame;h.get(U)!==S&&(h.set(U,S),U.update())}function Ae(U,S){const j=U.colorSpace,at=U.format,ht=U.type;return U.isCompressedTexture===!0||U.isVideoTexture===!0||j!==Hs&&j!==Ci&&(le.getTransfer(j)===we?(at!==Pn||ht!==fi)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",j)),S}function Ht(U){return typeof HTMLImageElement<"u"&&U instanceof HTMLImageElement?(l.width=U.naturalWidth||U.width,l.height=U.naturalHeight||U.height):typeof VideoFrame<"u"&&U instanceof VideoFrame?(l.width=U.displayWidth,l.height=U.displayHeight):(l.width=U.width,l.height=U.height),l}this.allocateTextureUnit=H,this.resetTextureUnits=k,this.setTexture2D=tt,this.setTexture2DArray=O,this.setTexture3D=et,this.setTextureCube=W,this.rebindTextures=Qt,this.setupRenderTarget=Re,this.updateRenderTargetMipmap=ue,this.updateMultisampleRenderTarget=on,this.setupDepthRenderbuffer=zt,this.setupFrameBufferTexture=nt,this.useMultisampledRTT=ce}function P0(i,t){function e(n,s=Ci){let r;const a=le.getTransfer(s);if(n===fi)return i.UNSIGNED_BYTE;if(n===Vc)return i.UNSIGNED_SHORT_4_4_4_4;if(n===Hc)return i.UNSIGNED_SHORT_5_5_5_1;if(n===ou)return i.UNSIGNED_INT_5_9_9_9_REV;if(n===ru)return i.BYTE;if(n===au)return i.SHORT;if(n===pr)return i.UNSIGNED_SHORT;if(n===zc)return i.INT;if(n===Ki)return i.UNSIGNED_INT;if(n===qn)return i.FLOAT;if(n===br)return i.HALF_FLOAT;if(n===cu)return i.ALPHA;if(n===lu)return i.RGB;if(n===Pn)return i.RGBA;if(n===hu)return i.LUMINANCE;if(n===uu)return i.LUMINANCE_ALPHA;if(n===Es)return i.DEPTH_COMPONENT;if(n===Ds)return i.DEPTH_STENCIL;if(n===du)return i.RED;if(n===Gc)return i.RED_INTEGER;if(n===fu)return i.RG;if(n===Wc)return i.RG_INTEGER;if(n===Xc)return i.RGBA_INTEGER;if(n===pa||n===ma||n===ga||n===_a)if(a===we)if(r=t.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(n===pa)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(n===ma)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(n===ga)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(n===_a)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=t.get("WEBGL_compressed_texture_s3tc"),r!==null){if(n===pa)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(n===ma)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(n===ga)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(n===_a)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(n===ac||n===oc||n===cc||n===lc)if(r=t.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(n===ac)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(n===oc)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(n===cc)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(n===lc)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(n===hc||n===uc||n===dc)if(r=t.get("WEBGL_compressed_texture_etc"),r!==null){if(n===hc||n===uc)return a===we?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(n===dc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(n===fc||n===pc||n===mc||n===gc||n===_c||n===vc||n===xc||n===yc||n===Mc||n===bc||n===Sc||n===Ec||n===wc||n===Tc)if(r=t.get("WEBGL_compressed_texture_astc"),r!==null){if(n===fc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(n===pc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(n===mc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(n===gc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(n===_c)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(n===vc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(n===xc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(n===yc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(n===Mc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(n===bc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(n===Sc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(n===Ec)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(n===wc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(n===Tc)return a===we?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(n===va||n===Ac||n===Cc)if(r=t.get("EXT_texture_compression_bptc"),r!==null){if(n===va)return a===we?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(n===Ac)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(n===Cc)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(n===pu||n===Rc||n===Pc||n===Lc)if(r=t.get("EXT_texture_compression_rgtc"),r!==null){if(n===va)return r.COMPRESSED_RED_RGTC1_EXT;if(n===Rc)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(n===Pc)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(n===Lc)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return n===Ns?i.UNSIGNED_INT_24_8:i[n]!==void 0?i[n]:null}return{convert:e}}class L0 extends tn{constructor(t=[]){super(),this.isArrayCamera=!0,this.cameras=t}}class ke extends De{constructor(){super(),this.isGroup=!0,this.type="Group"}}const N0={type:"move"};class Lo{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new ke,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new ke,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new D,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new D),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new ke,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new D,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new D),this._grip}dispatchEvent(t){return this._targetRay!==null&&this._targetRay.dispatchEvent(t),this._grip!==null&&this._grip.dispatchEvent(t),this._hand!==null&&this._hand.dispatchEvent(t),this}connect(t){if(t&&t.hand){const e=this._hand;if(e)for(const n of t.hand.values())this._getHandJoint(e,n)}return this.dispatchEvent({type:"connected",data:t}),this}disconnect(t){return this.dispatchEvent({type:"disconnected",data:t}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(t,e,n){let s=null,r=null,a=null;const o=this._targetRay,c=this._grip,l=this._hand;if(t&&e.session.visibilityState!=="visible-blurred"){if(l&&t.hand){a=!0;for(const _ of t.hand.values()){const m=e.getJointPose(_,n),p=this._getHandJoint(l,_);m!==null&&(p.matrix.fromArray(m.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,p.jointRadius=m.radius),p.visible=m!==null}const h=l.joints["index-finger-tip"],u=l.joints["thumb-tip"],d=h.position.distanceTo(u.position),f=.02,g=.005;l.inputState.pinching&&d>f+g?(l.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:t.handedness,target:this})):!l.inputState.pinching&&d<=f-g&&(l.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:t.handedness,target:this}))}else c!==null&&t.gripSpace&&(r=e.getPose(t.gripSpace,n),r!==null&&(c.matrix.fromArray(r.transform.matrix),c.matrix.decompose(c.position,c.rotation,c.scale),c.matrixWorldNeedsUpdate=!0,r.linearVelocity?(c.hasLinearVelocity=!0,c.linearVelocity.copy(r.linearVelocity)):c.hasLinearVelocity=!1,r.angularVelocity?(c.hasAngularVelocity=!0,c.angularVelocity.copy(r.angularVelocity)):c.hasAngularVelocity=!1));o!==null&&(s=e.getPose(t.targetRaySpace,n),s===null&&r!==null&&(s=r),s!==null&&(o.matrix.fromArray(s.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,s.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(s.linearVelocity)):o.hasLinearVelocity=!1,s.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(s.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(N0)))}return o!==null&&(o.visible=s!==null),c!==null&&(c.visible=r!==null),l!==null&&(l.visible=a!==null),this}_getHandJoint(t,e){if(t.joints[e.jointName]===void 0){const n=new ke;n.matrixAutoUpdate=!1,n.visible=!1,t.joints[e.jointName]=n,t.add(n)}return t.joints[e.jointName]}}const D0=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,I0=`
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

}`;class U0{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(t,e,n){if(this.texture===null){const s=new Je,r=t.properties.get(s);r.__webglTexture=e.texture,(e.depthNear!=n.depthNear||e.depthFar!=n.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=s}}getMesh(t){if(this.texture!==null&&this.mesh===null){const e=t.cameras[0].viewport,n=new Ni({vertexShader:D0,fragmentShader:I0,uniforms:{depthColor:{value:this.texture},depthWidth:{value:e.z},depthHeight:{value:e.w}}});this.mesh=new ge(new Ha(20,20),n)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}}class F0 extends ts{constructor(t,e){super();const n=this;let s=null,r=1,a=null,o="local-floor",c=1,l=null,h=null,u=null,d=null,f=null,g=null;const _=new U0,m=e.getContextAttributes();let p=null,P=null;const w=[],y=[],N=new At;let C=null;const L=new tn;L.viewport=new ye;const I=new tn;I.viewport=new ye;const M=[L,I],b=new L0;let F=null,k=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(q){let J=w[q];return J===void 0&&(J=new Lo,w[q]=J),J.getTargetRaySpace()},this.getControllerGrip=function(q){let J=w[q];return J===void 0&&(J=new Lo,w[q]=J),J.getGripSpace()},this.getHand=function(q){let J=w[q];return J===void 0&&(J=new Lo,w[q]=J),J.getHandSpace()};function H(q){const J=y.indexOf(q.inputSource);if(J===-1)return;const nt=w[J];nt!==void 0&&(nt.update(q.inputSource,q.frame,l||a),nt.dispatchEvent({type:q.type,data:q.inputSource}))}function Z(){s.removeEventListener("select",H),s.removeEventListener("selectstart",H),s.removeEventListener("selectend",H),s.removeEventListener("squeeze",H),s.removeEventListener("squeezestart",H),s.removeEventListener("squeezeend",H),s.removeEventListener("end",Z),s.removeEventListener("inputsourceschange",tt);for(let q=0;q<w.length;q++){const J=y[q];J!==null&&(y[q]=null,w[q].disconnect(J))}F=null,k=null,_.reset(),t.setRenderTarget(p),f=null,d=null,u=null,s=null,P=null,wt.stop(),n.isPresenting=!1,t.setPixelRatio(C),t.setSize(N.width,N.height,!1),n.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(q){r=q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(q){o=q,n.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return l||a},this.setReferenceSpace=function(q){l=q},this.getBaseLayer=function(){return d!==null?d:f},this.getBinding=function(){return u},this.getFrame=function(){return g},this.getSession=function(){return s},this.setSession=async function(q){if(s=q,s!==null){if(p=t.getRenderTarget(),s.addEventListener("select",H),s.addEventListener("selectstart",H),s.addEventListener("selectend",H),s.addEventListener("squeeze",H),s.addEventListener("squeezestart",H),s.addEventListener("squeezeend",H),s.addEventListener("end",Z),s.addEventListener("inputsourceschange",tt),m.xrCompatible!==!0&&await e.makeXRCompatible(),C=t.getPixelRatio(),t.getSize(N),s.renderState.layers===void 0){const J={antialias:m.antialias,alpha:!0,depth:m.depth,stencil:m.stencil,framebufferScaleFactor:r};f=new XRWebGLLayer(s,e,J),s.updateRenderState({baseLayer:f}),t.setPixelRatio(1),t.setSize(f.framebufferWidth,f.framebufferHeight,!1),P=new Ji(f.framebufferWidth,f.framebufferHeight,{format:Pn,type:fi,colorSpace:t.outputColorSpace,stencilBuffer:m.stencil})}else{let J=null,nt=null,it=null;m.depth&&(it=m.stencil?e.DEPTH24_STENCIL8:e.DEPTH_COMPONENT24,J=m.stencil?Ds:Es,nt=m.stencil?Ns:Ki);const vt={colorFormat:e.RGBA8,depthFormat:it,scaleFactor:r};u=new XRWebGLBinding(s,e),d=u.createProjectionLayer(vt),s.updateRenderState({layers:[d]}),t.setPixelRatio(1),t.setSize(d.textureWidth,d.textureHeight,!1),P=new Ji(d.textureWidth,d.textureHeight,{format:Pn,type:fi,depthTexture:new Tu(d.textureWidth,d.textureHeight,nt,void 0,void 0,void 0,void 0,void 0,void 0,J),stencilBuffer:m.stencil,colorSpace:t.outputColorSpace,samples:m.antialias?4:0,resolveDepthBuffer:d.ignoreDepthValues===!1})}P.isXRRenderTarget=!0,this.setFoveation(c),l=null,a=await s.requestReferenceSpace(o),wt.setContext(s),wt.start(),n.isPresenting=!0,n.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(s!==null)return s.environmentBlendMode},this.getDepthTexture=function(){return _.getDepthTexture()};function tt(q){for(let J=0;J<q.removed.length;J++){const nt=q.removed[J],it=y.indexOf(nt);it>=0&&(y[it]=null,w[it].disconnect(nt))}for(let J=0;J<q.added.length;J++){const nt=q.added[J];let it=y.indexOf(nt);if(it===-1){for(let zt=0;zt<w.length;zt++)if(zt>=y.length){y.push(nt),it=zt;break}else if(y[zt]===null){y[zt]=nt,it=zt;break}if(it===-1)break}const vt=w[it];vt&&vt.connect(nt)}}const O=new D,et=new D;function W(q,J,nt){O.setFromMatrixPosition(J.matrixWorld),et.setFromMatrixPosition(nt.matrixWorld);const it=O.distanceTo(et),vt=J.projectionMatrix.elements,zt=nt.projectionMatrix.elements,Qt=vt[14]/(vt[10]-1),Re=vt[14]/(vt[10]+1),ue=(vt[9]+1)/vt[5],Ie=(vt[9]-1)/vt[5],G=(vt[8]-1)/vt[0],on=(zt[8]+1)/zt[0],oe=Qt*G,ce=Qt*on,Wt=it/(-G+on),Ae=Wt*-G;if(J.matrixWorld.decompose(q.position,q.quaternion,q.scale),q.translateX(Ae),q.translateZ(Wt),q.matrixWorld.compose(q.position,q.quaternion,q.scale),q.matrixWorldInverse.copy(q.matrixWorld).invert(),vt[10]===-1)q.projectionMatrix.copy(J.projectionMatrix),q.projectionMatrixInverse.copy(J.projectionMatrixInverse);else{const Ht=Qt+Wt,U=Re+Wt,S=oe-Ae,j=ce+(it-Ae),at=ue*Re/U*Ht,ht=Ie*Re/U*Ht;q.projectionMatrix.makePerspective(S,j,at,ht,Ht,U),q.projectionMatrixInverse.copy(q.projectionMatrix).invert()}}function lt(q,J){J===null?q.matrixWorld.copy(q.matrix):q.matrixWorld.multiplyMatrices(J.matrixWorld,q.matrix),q.matrixWorldInverse.copy(q.matrixWorld).invert()}this.updateCamera=function(q){if(s===null)return;let J=q.near,nt=q.far;_.texture!==null&&(_.depthNear>0&&(J=_.depthNear),_.depthFar>0&&(nt=_.depthFar)),b.near=I.near=L.near=J,b.far=I.far=L.far=nt,(F!==b.near||k!==b.far)&&(s.updateRenderState({depthNear:b.near,depthFar:b.far}),F=b.near,k=b.far),L.layers.mask=q.layers.mask|2,I.layers.mask=q.layers.mask|4,b.layers.mask=L.layers.mask|I.layers.mask;const it=q.parent,vt=b.cameras;lt(b,it);for(let zt=0;zt<vt.length;zt++)lt(vt[zt],it);vt.length===2?W(b,L,I):b.projectionMatrix.copy(L.projectionMatrix),pt(q,b,it)};function pt(q,J,nt){nt===null?q.matrix.copy(J.matrixWorld):(q.matrix.copy(nt.matrixWorld),q.matrix.invert(),q.matrix.multiply(J.matrixWorld)),q.matrix.decompose(q.position,q.quaternion,q.scale),q.updateMatrixWorld(!0),q.projectionMatrix.copy(J.projectionMatrix),q.projectionMatrixInverse.copy(J.projectionMatrixInverse),q.isPerspectiveCamera&&(q.fov=Is*2*Math.atan(1/q.projectionMatrix.elements[5]),q.zoom=1)}this.getCamera=function(){return b},this.getFoveation=function(){if(!(d===null&&f===null))return c},this.setFoveation=function(q){c=q,d!==null&&(d.fixedFoveation=q),f!==null&&f.fixedFoveation!==void 0&&(f.fixedFoveation=q)},this.hasDepthSensing=function(){return _.texture!==null},this.getDepthSensingMesh=function(){return _.getMesh(b)};let mt=null;function Rt(q,J){if(h=J.getViewerPose(l||a),g=J,h!==null){const nt=h.views;f!==null&&(t.setRenderTargetFramebuffer(P,f.framebuffer),t.setRenderTarget(P));let it=!1;nt.length!==b.cameras.length&&(b.cameras.length=0,it=!0);for(let zt=0;zt<nt.length;zt++){const Qt=nt[zt];let Re=null;if(f!==null)Re=f.getViewport(Qt);else{const Ie=u.getViewSubImage(d,Qt);Re=Ie.viewport,zt===0&&(t.setRenderTargetTextures(P,Ie.colorTexture,d.ignoreDepthValues?void 0:Ie.depthStencilTexture),t.setRenderTarget(P))}let ue=M[zt];ue===void 0&&(ue=new tn,ue.layers.enable(zt),ue.viewport=new ye,M[zt]=ue),ue.matrix.fromArray(Qt.transform.matrix),ue.matrix.decompose(ue.position,ue.quaternion,ue.scale),ue.projectionMatrix.fromArray(Qt.projectionMatrix),ue.projectionMatrixInverse.copy(ue.projectionMatrix).invert(),ue.viewport.set(Re.x,Re.y,Re.width,Re.height),zt===0&&(b.matrix.copy(ue.matrix),b.matrix.decompose(b.position,b.quaternion,b.scale)),it===!0&&b.cameras.push(ue)}const vt=s.enabledFeatures;if(vt&&vt.includes("depth-sensing")){const zt=u.getDepthInformation(nt[0]);zt&&zt.isValid&&zt.texture&&_.init(t,zt,s.renderState)}}for(let nt=0;nt<w.length;nt++){const it=y[nt],vt=w[nt];it!==null&&vt!==void 0&&vt.update(it,J,l||a)}mt&&mt(q,J),J.detectedPlanes&&n.dispatchEvent({type:"planesdetected",data:J}),g=null}const wt=new wu;wt.setAnimationLoop(Rt),this.setAnimationLoop=function(q){mt=q},this.dispose=function(){}}}const Wi=new pn,O0=new Yt;function k0(i,t){function e(m,p){m.matrixAutoUpdate===!0&&m.updateMatrix(),p.value.copy(m.matrix)}function n(m,p){p.color.getRGB(m.fogColor.value,bu(i)),p.isFog?(m.fogNear.value=p.near,m.fogFar.value=p.far):p.isFogExp2&&(m.fogDensity.value=p.density)}function s(m,p,P,w,y){p.isMeshBasicMaterial||p.isMeshLambertMaterial?r(m,p):p.isMeshToonMaterial?(r(m,p),u(m,p)):p.isMeshPhongMaterial?(r(m,p),h(m,p)):p.isMeshStandardMaterial?(r(m,p),d(m,p),p.isMeshPhysicalMaterial&&f(m,p,y)):p.isMeshMatcapMaterial?(r(m,p),g(m,p)):p.isMeshDepthMaterial?r(m,p):p.isMeshDistanceMaterial?(r(m,p),_(m,p)):p.isMeshNormalMaterial?r(m,p):p.isLineBasicMaterial?(a(m,p),p.isLineDashedMaterial&&o(m,p)):p.isPointsMaterial?c(m,p,P,w):p.isSpriteMaterial?l(m,p):p.isShadowMaterial?(m.color.value.copy(p.color),m.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function r(m,p){m.opacity.value=p.opacity,p.color&&m.diffuse.value.copy(p.color),p.emissive&&m.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(m.map.value=p.map,e(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.bumpMap&&(m.bumpMap.value=p.bumpMap,e(p.bumpMap,m.bumpMapTransform),m.bumpScale.value=p.bumpScale,p.side===fn&&(m.bumpScale.value*=-1)),p.normalMap&&(m.normalMap.value=p.normalMap,e(p.normalMap,m.normalMapTransform),m.normalScale.value.copy(p.normalScale),p.side===fn&&m.normalScale.value.negate()),p.displacementMap&&(m.displacementMap.value=p.displacementMap,e(p.displacementMap,m.displacementMapTransform),m.displacementScale.value=p.displacementScale,m.displacementBias.value=p.displacementBias),p.emissiveMap&&(m.emissiveMap.value=p.emissiveMap,e(p.emissiveMap,m.emissiveMapTransform)),p.specularMap&&(m.specularMap.value=p.specularMap,e(p.specularMap,m.specularMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest);const P=t.get(p),w=P.envMap,y=P.envMapRotation;w&&(m.envMap.value=w,Wi.copy(y),Wi.x*=-1,Wi.y*=-1,Wi.z*=-1,w.isCubeTexture&&w.isRenderTargetTexture===!1&&(Wi.y*=-1,Wi.z*=-1),m.envMapRotation.value.setFromMatrix4(O0.makeRotationFromEuler(Wi)),m.flipEnvMap.value=w.isCubeTexture&&w.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=p.reflectivity,m.ior.value=p.ior,m.refractionRatio.value=p.refractionRatio),p.lightMap&&(m.lightMap.value=p.lightMap,m.lightMapIntensity.value=p.lightMapIntensity,e(p.lightMap,m.lightMapTransform)),p.aoMap&&(m.aoMap.value=p.aoMap,m.aoMapIntensity.value=p.aoMapIntensity,e(p.aoMap,m.aoMapTransform))}function a(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,p.map&&(m.map.value=p.map,e(p.map,m.mapTransform))}function o(m,p){m.dashSize.value=p.dashSize,m.totalSize.value=p.dashSize+p.gapSize,m.scale.value=p.scale}function c(m,p,P,w){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.size.value=p.size*P,m.scale.value=w*.5,p.map&&(m.map.value=p.map,e(p.map,m.uvTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function l(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.rotation.value=p.rotation,p.map&&(m.map.value=p.map,e(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,e(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function h(m,p){m.specular.value.copy(p.specular),m.shininess.value=Math.max(p.shininess,1e-4)}function u(m,p){p.gradientMap&&(m.gradientMap.value=p.gradientMap)}function d(m,p){m.metalness.value=p.metalness,p.metalnessMap&&(m.metalnessMap.value=p.metalnessMap,e(p.metalnessMap,m.metalnessMapTransform)),m.roughness.value=p.roughness,p.roughnessMap&&(m.roughnessMap.value=p.roughnessMap,e(p.roughnessMap,m.roughnessMapTransform)),p.envMap&&(m.envMapIntensity.value=p.envMapIntensity)}function f(m,p,P){m.ior.value=p.ior,p.sheen>0&&(m.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),m.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(m.sheenColorMap.value=p.sheenColorMap,e(p.sheenColorMap,m.sheenColorMapTransform)),p.sheenRoughnessMap&&(m.sheenRoughnessMap.value=p.sheenRoughnessMap,e(p.sheenRoughnessMap,m.sheenRoughnessMapTransform))),p.clearcoat>0&&(m.clearcoat.value=p.clearcoat,m.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(m.clearcoatMap.value=p.clearcoatMap,e(p.clearcoatMap,m.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,e(p.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(m.clearcoatNormalMap.value=p.clearcoatNormalMap,e(p.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===fn&&m.clearcoatNormalScale.value.negate())),p.dispersion>0&&(m.dispersion.value=p.dispersion),p.iridescence>0&&(m.iridescence.value=p.iridescence,m.iridescenceIOR.value=p.iridescenceIOR,m.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(m.iridescenceMap.value=p.iridescenceMap,e(p.iridescenceMap,m.iridescenceMapTransform)),p.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=p.iridescenceThicknessMap,e(p.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),p.transmission>0&&(m.transmission.value=p.transmission,m.transmissionSamplerMap.value=P.texture,m.transmissionSamplerSize.value.set(P.width,P.height),p.transmissionMap&&(m.transmissionMap.value=p.transmissionMap,e(p.transmissionMap,m.transmissionMapTransform)),m.thickness.value=p.thickness,p.thicknessMap&&(m.thicknessMap.value=p.thicknessMap,e(p.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=p.attenuationDistance,m.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(m.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(m.anisotropyMap.value=p.anisotropyMap,e(p.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=p.specularIntensity,m.specularColor.value.copy(p.specularColor),p.specularColorMap&&(m.specularColorMap.value=p.specularColorMap,e(p.specularColorMap,m.specularColorMapTransform)),p.specularIntensityMap&&(m.specularIntensityMap.value=p.specularIntensityMap,e(p.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,p){p.matcap&&(m.matcap.value=p.matcap)}function _(m,p){const P=t.get(p).light;m.referencePosition.value.setFromMatrixPosition(P.matrixWorld),m.nearDistance.value=P.shadow.camera.near,m.farDistance.value=P.shadow.camera.far}return{refreshFogUniforms:n,refreshMaterialUniforms:s}}function B0(i,t,e,n){let s={},r={},a=[];const o=i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS);function c(P,w){const y=w.program;n.uniformBlockBinding(P,y)}function l(P,w){let y=s[P.id];y===void 0&&(g(P),y=h(P),s[P.id]=y,P.addEventListener("dispose",m));const N=w.program;n.updateUBOMapping(P,N);const C=t.render.frame;r[P.id]!==C&&(d(P),r[P.id]=C)}function h(P){const w=u();P.__bindingPointIndex=w;const y=i.createBuffer(),N=P.__size,C=P.usage;return i.bindBuffer(i.UNIFORM_BUFFER,y),i.bufferData(i.UNIFORM_BUFFER,N,C),i.bindBuffer(i.UNIFORM_BUFFER,null),i.bindBufferBase(i.UNIFORM_BUFFER,w,y),y}function u(){for(let P=0;P<o;P++)if(a.indexOf(P)===-1)return a.push(P),P;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function d(P){const w=s[P.id],y=P.uniforms,N=P.__cache;i.bindBuffer(i.UNIFORM_BUFFER,w);for(let C=0,L=y.length;C<L;C++){const I=Array.isArray(y[C])?y[C]:[y[C]];for(let M=0,b=I.length;M<b;M++){const F=I[M];if(f(F,C,M,N)===!0){const k=F.__offset,H=Array.isArray(F.value)?F.value:[F.value];let Z=0;for(let tt=0;tt<H.length;tt++){const O=H[tt],et=_(O);typeof O=="number"||typeof O=="boolean"?(F.__data[0]=O,i.bufferSubData(i.UNIFORM_BUFFER,k+Z,F.__data)):O.isMatrix3?(F.__data[0]=O.elements[0],F.__data[1]=O.elements[1],F.__data[2]=O.elements[2],F.__data[3]=0,F.__data[4]=O.elements[3],F.__data[5]=O.elements[4],F.__data[6]=O.elements[5],F.__data[7]=0,F.__data[8]=O.elements[6],F.__data[9]=O.elements[7],F.__data[10]=O.elements[8],F.__data[11]=0):(O.toArray(F.__data,Z),Z+=et.storage/Float32Array.BYTES_PER_ELEMENT)}i.bufferSubData(i.UNIFORM_BUFFER,k,F.__data)}}}i.bindBuffer(i.UNIFORM_BUFFER,null)}function f(P,w,y,N){const C=P.value,L=w+"_"+y;if(N[L]===void 0)return typeof C=="number"||typeof C=="boolean"?N[L]=C:N[L]=C.clone(),!0;{const I=N[L];if(typeof C=="number"||typeof C=="boolean"){if(I!==C)return N[L]=C,!0}else if(I.equals(C)===!1)return I.copy(C),!0}return!1}function g(P){const w=P.uniforms;let y=0;const N=16;for(let L=0,I=w.length;L<I;L++){const M=Array.isArray(w[L])?w[L]:[w[L]];for(let b=0,F=M.length;b<F;b++){const k=M[b],H=Array.isArray(k.value)?k.value:[k.value];for(let Z=0,tt=H.length;Z<tt;Z++){const O=H[Z],et=_(O),W=y%N,lt=W%et.boundary,pt=W+lt;y+=lt,pt!==0&&N-pt<et.storage&&(y+=N-pt),k.__data=new Float32Array(et.storage/Float32Array.BYTES_PER_ELEMENT),k.__offset=y,y+=et.storage}}}const C=y%N;return C>0&&(y+=N-C),P.__size=y,P.__cache={},this}function _(P){const w={boundary:0,storage:0};return typeof P=="number"||typeof P=="boolean"?(w.boundary=4,w.storage=4):P.isVector2?(w.boundary=8,w.storage=8):P.isVector3||P.isColor?(w.boundary=16,w.storage=12):P.isVector4?(w.boundary=16,w.storage=16):P.isMatrix3?(w.boundary=48,w.storage=48):P.isMatrix4?(w.boundary=64,w.storage=64):P.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",P),w}function m(P){const w=P.target;w.removeEventListener("dispose",m);const y=a.indexOf(w.__bindingPointIndex);a.splice(y,1),i.deleteBuffer(s[w.id]),delete s[w.id],delete r[w.id]}function p(){for(const P in s)i.deleteBuffer(s[P]);a=[],s={},r={}}return{bind:c,update:l,dispose:p}}class z0{constructor(t={}){const{canvas:e=Cf(),context:n=null,depth:s=!0,stencil:r=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:c=!0,preserveDrawingBuffer:l=!1,powerPreference:h="default",failIfMajorPerformanceCaveat:u=!1,reverseDepthBuffer:d=!1}=t;this.isWebGLRenderer=!0;let f;if(n!==null){if(typeof WebGLRenderingContext<"u"&&n instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");f=n.getContextAttributes().alpha}else f=a;const g=new Uint32Array(4),_=new Int32Array(4);let m=null,p=null;const P=[],w=[];this.domElement=e,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this._outputColorSpace=Ne,this.toneMapping=Li,this.toneMappingExposure=1;const y=this;let N=!1,C=0,L=0,I=null,M=-1,b=null;const F=new ye,k=new ye;let H=null;const Z=new Jt(0);let tt=0,O=e.width,et=e.height,W=1,lt=null,pt=null;const mt=new ye(0,0,O,et),Rt=new ye(0,0,O,et);let wt=!1;const q=new Yc;let J=!1,nt=!1;const it=new Yt,vt=new Yt,zt=new D,Qt=new ye,Re={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0};let ue=!1;function Ie(){return I===null?W:1}let G=n;function on(A,V){return e.getContext(A,V)}try{const A={alpha:!0,depth:s,stencil:r,antialias:o,premultipliedAlpha:c,preserveDrawingBuffer:l,powerPreference:h,failIfMajorPerformanceCaveat:u};if("setAttribute"in e&&e.setAttribute("data-engine",`three.js r${Bc}`),e.addEventListener("webglcontextlost",ot,!1),e.addEventListener("webglcontextrestored",Et,!1),e.addEventListener("webglcontextcreationerror",bt,!1),G===null){const V="webgl2";if(G=on(V,A),G===null)throw on(V)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(A){throw console.error("THREE.WebGLRenderer: "+A.message),A}let oe,ce,Wt,Ae,Ht,U,S,j,at,ht,rt,Ft,Mt,Ct,de,ft,Pt,Xt,$t,Lt,he,ne,Me,z;function xt(){oe=new Xg(G),oe.init(),ne=new P0(G,oe),ce=new Bg(G,oe,t,ne),Wt=new A0(G,oe),ce.reverseDepthBuffer&&d&&Wt.buffers.depth.setReversed(!0),Ae=new Yg(G),Ht=new d0,U=new R0(G,oe,Wt,Ht,ce,ne,Ae),S=new Vg(y),j=new Wg(y),at=new ep(G),Me=new Og(G,at),ht=new qg(G,at,Ae,Me),rt=new Kg(G,ht,at,Ae),$t=new $g(G,ce,U),ft=new zg(Ht),Ft=new u0(y,S,j,oe,ce,Me,ft),Mt=new k0(y,Ht),Ct=new p0,de=new y0(oe),Xt=new Fg(y,S,j,Wt,rt,f,c),Pt=new w0(y,rt,ce),z=new B0(G,Ae,ce,Wt),Lt=new kg(G,oe,Ae),he=new jg(G,oe,Ae),Ae.programs=Ft.programs,y.capabilities=ce,y.extensions=oe,y.properties=Ht,y.renderLists=Ct,y.shadowMap=Pt,y.state=Wt,y.info=Ae}xt();const Q=new F0(y,G);this.xr=Q,this.getContext=function(){return G},this.getContextAttributes=function(){return G.getContextAttributes()},this.forceContextLoss=function(){const A=oe.get("WEBGL_lose_context");A&&A.loseContext()},this.forceContextRestore=function(){const A=oe.get("WEBGL_lose_context");A&&A.restoreContext()},this.getPixelRatio=function(){return W},this.setPixelRatio=function(A){A!==void 0&&(W=A,this.setSize(O,et,!1))},this.getSize=function(A){return A.set(O,et)},this.setSize=function(A,V,Y=!0){if(Q.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}O=A,et=V,e.width=Math.floor(A*W),e.height=Math.floor(V*W),Y===!0&&(e.style.width=A+"px",e.style.height=V+"px"),this.setViewport(0,0,A,V)},this.getDrawingBufferSize=function(A){return A.set(O*W,et*W).floor()},this.setDrawingBufferSize=function(A,V,Y){O=A,et=V,W=Y,e.width=Math.floor(A*Y),e.height=Math.floor(V*Y),this.setViewport(0,0,A,V)},this.getCurrentViewport=function(A){return A.copy(F)},this.getViewport=function(A){return A.copy(mt)},this.setViewport=function(A,V,Y,$){A.isVector4?mt.set(A.x,A.y,A.z,A.w):mt.set(A,V,Y,$),Wt.viewport(F.copy(mt).multiplyScalar(W).round())},this.getScissor=function(A){return A.copy(Rt)},this.setScissor=function(A,V,Y,$){A.isVector4?Rt.set(A.x,A.y,A.z,A.w):Rt.set(A,V,Y,$),Wt.scissor(k.copy(Rt).multiplyScalar(W).round())},this.getScissorTest=function(){return wt},this.setScissorTest=function(A){Wt.setScissorTest(wt=A)},this.setOpaqueSort=function(A){lt=A},this.setTransparentSort=function(A){pt=A},this.getClearColor=function(A){return A.copy(Xt.getClearColor())},this.setClearColor=function(){Xt.setClearColor.apply(Xt,arguments)},this.getClearAlpha=function(){return Xt.getClearAlpha()},this.setClearAlpha=function(){Xt.setClearAlpha.apply(Xt,arguments)},this.clear=function(A=!0,V=!0,Y=!0){let $=0;if(A){let B=!1;if(I!==null){const dt=I.texture.format;B=dt===Xc||dt===Wc||dt===Gc}if(B){const dt=I.texture.type,yt=dt===fi||dt===Ki||dt===pr||dt===Ns||dt===Vc||dt===Hc,Dt=Xt.getClearColor(),It=Xt.getClearAlpha(),Kt=Dt.r,ee=Dt.g,Ut=Dt.b;yt?(g[0]=Kt,g[1]=ee,g[2]=Ut,g[3]=It,G.clearBufferuiv(G.COLOR,0,g)):(_[0]=Kt,_[1]=ee,_[2]=Ut,_[3]=It,G.clearBufferiv(G.COLOR,0,_))}else $|=G.COLOR_BUFFER_BIT}V&&($|=G.DEPTH_BUFFER_BIT),Y&&($|=G.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),G.clear($)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){e.removeEventListener("webglcontextlost",ot,!1),e.removeEventListener("webglcontextrestored",Et,!1),e.removeEventListener("webglcontextcreationerror",bt,!1),Ct.dispose(),de.dispose(),Ht.dispose(),S.dispose(),j.dispose(),rt.dispose(),Me.dispose(),z.dispose(),Ft.dispose(),Q.dispose(),Q.removeEventListener("sessionstart",Tr),Q.removeEventListener("sessionend",Ar),Zn.stop()};function ot(A){A.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),N=!0}function Et(){console.log("THREE.WebGLRenderer: Context Restored."),N=!1;const A=Ae.autoReset,V=Pt.enabled,Y=Pt.autoUpdate,$=Pt.needsUpdate,B=Pt.type;xt(),Ae.autoReset=A,Pt.enabled=V,Pt.autoUpdate=Y,Pt.needsUpdate=$,Pt.type=B}function bt(A){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",A.statusMessage)}function te(A){const V=A.target;V.removeEventListener("dispose",te),Pe(V)}function Pe(A){qe(A),Ht.remove(A)}function qe(A){const V=Ht.get(A).programs;V!==void 0&&(V.forEach(function(Y){Ft.releaseProgram(Y)}),A.isShaderMaterial&&Ft.releaseShaderCache(A))}this.renderBufferDirect=function(A,V,Y,$,B,dt){V===null&&(V=Re);const yt=B.isMesh&&B.matrixWorld.determinant()<0,Dt=Qa(A,V,Y,$,B);Wt.setMaterial($,yt);let It=Y.index,Kt=1;if($.wireframe===!0){if(It=ht.getWireframeAttribute(Y),It===void 0)return;Kt=2}const ee=Y.drawRange,Ut=Y.attributes.position;let pe=ee.start*Kt,be=(ee.start+ee.count)*Kt;dt!==null&&(pe=Math.max(pe,dt.start*Kt),be=Math.min(be,(dt.start+dt.count)*Kt)),It!==null?(pe=Math.max(pe,0),be=Math.min(be,It.count)):Ut!=null&&(pe=Math.max(pe,0),be=Math.min(be,Ut.count));const Ee=be-pe;if(Ee<0||Ee===1/0)return;Me.setup(B,$,Dt,Y,It);let Be,_e=Lt;if(It!==null&&(Be=at.get(It),_e=he,_e.setIndex(Be)),B.isMesh)$.wireframe===!0?(Wt.setLineWidth($.wireframeLinewidth*Ie()),_e.setMode(G.LINES)):_e.setMode(G.TRIANGLES);else if(B.isLine){let Ot=$.linewidth;Ot===void 0&&(Ot=1),Wt.setLineWidth(Ot*Ie()),B.isLineSegments?_e.setMode(G.LINES):B.isLineLoop?_e.setMode(G.LINE_LOOP):_e.setMode(G.LINE_STRIP)}else B.isPoints?_e.setMode(G.POINTS):B.isSprite&&_e.setMode(G.TRIANGLES);if(B.isBatchedMesh)if(B._multiDrawInstances!==null)_e.renderMultiDrawInstances(B._multiDrawStarts,B._multiDrawCounts,B._multiDrawCount,B._multiDrawInstances);else if(oe.get("WEBGL_multi_draw"))_e.renderMultiDraw(B._multiDrawStarts,B._multiDrawCounts,B._multiDrawCount);else{const Ot=B._multiDrawStarts,Dn=B._multiDrawCounts,me=B._multiDrawCount,gn=It?at.get(It).bytesPerElement:1,_i=Ht.get($).currentProgram.getUniforms();for(let en=0;en<me;en++)_i.setValue(G,"_gl_DrawID",en),_e.render(Ot[en]/gn,Dn[en])}else if(B.isInstancedMesh)_e.renderInstances(pe,Ee,B.count);else if(Y.isInstancedBufferGeometry){const Ot=Y._maxInstanceCount!==void 0?Y._maxInstanceCount:1/0,Dn=Math.min(Y.instanceCount,Ot);_e.renderInstances(pe,Ee,Dn)}else _e.render(pe,Ee)};function se(A,V,Y){A.transparent===!0&&A.side===dn&&A.forceSinglePass===!1?(A.side=fn,A.needsUpdate=!0,is(A,V,Y),A.side=di,A.needsUpdate=!0,is(A,V,Y),A.side=dn):is(A,V,Y)}this.compile=function(A,V,Y=null){Y===null&&(Y=A),p=de.get(Y),p.init(V),w.push(p),Y.traverseVisible(function(B){B.isLight&&B.layers.test(V.layers)&&(p.pushLight(B),B.castShadow&&p.pushShadow(B))}),A!==Y&&A.traverseVisible(function(B){B.isLight&&B.layers.test(V.layers)&&(p.pushLight(B),B.castShadow&&p.pushShadow(B))}),p.setupLights();const $=new Set;return A.traverse(function(B){if(!(B.isMesh||B.isPoints||B.isLine||B.isSprite))return;const dt=B.material;if(dt)if(Array.isArray(dt))for(let yt=0;yt<dt.length;yt++){const Dt=dt[yt];se(Dt,Y,B),$.add(Dt)}else se(dt,Y,B),$.add(dt)}),w.pop(),p=null,$},this.compileAsync=function(A,V,Y=null){const $=this.compile(A,V,Y);return new Promise(B=>{function dt(){if($.forEach(function(yt){Ht.get(yt).currentProgram.isReady()&&$.delete(yt)}),$.size===0){B(A);return}setTimeout(dt,10)}oe.get("KHR_parallel_shader_compile")!==null?dt():setTimeout(dt,10)})};let cn=null;function Nn(A){cn&&cn(A)}function Tr(){Zn.stop()}function Ar(){Zn.start()}const Zn=new wu;Zn.setAnimationLoop(Nn),typeof self<"u"&&Zn.setContext(self),this.setAnimationLoop=function(A){cn=A,Q.setAnimationLoop(A),A===null?Zn.stop():Zn.start()},Q.addEventListener("sessionstart",Tr),Q.addEventListener("sessionend",Ar),this.render=function(A,V){if(V!==void 0&&V.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(N===!0)return;if(A.matrixWorldAutoUpdate===!0&&A.updateMatrixWorld(),V.parent===null&&V.matrixWorldAutoUpdate===!0&&V.updateMatrixWorld(),Q.enabled===!0&&Q.isPresenting===!0&&(Q.cameraAutoUpdate===!0&&Q.updateCamera(V),V=Q.getCamera()),A.isScene===!0&&A.onBeforeRender(y,A,V,I),p=de.get(A,w.length),p.init(V),w.push(p),vt.multiplyMatrices(V.projectionMatrix,V.matrixWorldInverse),q.setFromProjectionMatrix(vt),nt=this.localClippingEnabled,J=ft.init(this.clippingPlanes,nt),m=Ct.get(A,P.length),m.init(),P.push(m),Q.enabled===!0&&Q.isPresenting===!0){const dt=y.xr.getDepthSensingMesh();dt!==null&&Ks(dt,V,-1/0,y.sortObjects)}Ks(A,V,0,y.sortObjects),m.finish(),y.sortObjects===!0&&m.sort(lt,pt),ue=Q.enabled===!1||Q.isPresenting===!1||Q.hasDepthSensing()===!1,ue&&Xt.addToRenderList(m,A),this.info.render.frame++,J===!0&&ft.beginShadows();const Y=p.state.shadowsArray;Pt.render(Y,A,V),J===!0&&ft.endShadows(),this.info.autoReset===!0&&this.info.reset();const $=m.opaque,B=m.transmissive;if(p.setupLights(),V.isArrayCamera){const dt=V.cameras;if(B.length>0)for(let yt=0,Dt=dt.length;yt<Dt;yt++){const It=dt[yt];Js($,B,A,It)}ue&&Xt.render(A);for(let yt=0,Dt=dt.length;yt<Dt;yt++){const It=dt[yt];Cr(m,A,It,It.viewport)}}else B.length>0&&Js($,B,A,V),ue&&Xt.render(A),Cr(m,A,V);I!==null&&(U.updateMultisampleRenderTarget(I),U.updateRenderTargetMipmap(I)),A.isScene===!0&&A.onAfterRender(y,A,V),Me.resetDefaultState(),M=-1,b=null,w.pop(),w.length>0?(p=w[w.length-1],J===!0&&ft.setGlobalState(y.clippingPlanes,p.state.camera)):p=null,P.pop(),P.length>0?m=P[P.length-1]:m=null};function Ks(A,V,Y,$){if(A.visible===!1)return;if(A.layers.test(V.layers)){if(A.isGroup)Y=A.renderOrder;else if(A.isLOD)A.autoUpdate===!0&&A.update(V);else if(A.isLight)p.pushLight(A),A.castShadow&&p.pushShadow(A);else if(A.isSprite){if(!A.frustumCulled||q.intersectsSprite(A)){$&&Qt.setFromMatrixPosition(A.matrixWorld).applyMatrix4(vt);const yt=rt.update(A),Dt=A.material;Dt.visible&&m.push(A,yt,Dt,Y,Qt.z,null)}}else if((A.isMesh||A.isLine||A.isPoints)&&(!A.frustumCulled||q.intersectsObject(A))){const yt=rt.update(A),Dt=A.material;if($&&(A.boundingSphere!==void 0?(A.boundingSphere===null&&A.computeBoundingSphere(),Qt.copy(A.boundingSphere.center)):(yt.boundingSphere===null&&yt.computeBoundingSphere(),Qt.copy(yt.boundingSphere.center)),Qt.applyMatrix4(A.matrixWorld).applyMatrix4(vt)),Array.isArray(Dt)){const It=yt.groups;for(let Kt=0,ee=It.length;Kt<ee;Kt++){const Ut=It[Kt],pe=Dt[Ut.materialIndex];pe&&pe.visible&&m.push(A,yt,pe,Y,Qt.z,Ut)}}else Dt.visible&&m.push(A,yt,Dt,Y,Qt.z,null)}}const dt=A.children;for(let yt=0,Dt=dt.length;yt<Dt;yt++)Ks(dt[yt],V,Y,$)}function Cr(A,V,Y,$){const B=A.opaque,dt=A.transmissive,yt=A.transparent;p.setupLightsView(Y),J===!0&&ft.setGlobalState(y.clippingPlanes,Y),$&&Wt.viewport(F.copy($)),B.length>0&&ns(B,V,Y),dt.length>0&&ns(dt,V,Y),yt.length>0&&ns(yt,V,Y),Wt.buffers.depth.setTest(!0),Wt.buffers.depth.setMask(!0),Wt.buffers.color.setMask(!0),Wt.setPolygonOffset(!1)}function Js(A,V,Y,$){if((Y.isScene===!0?Y.overrideMaterial:null)!==null)return;p.state.transmissionRenderTarget[$.id]===void 0&&(p.state.transmissionRenderTarget[$.id]=new Ji(1,1,{generateMipmaps:!0,type:oe.has("EXT_color_buffer_half_float")||oe.has("EXT_color_buffer_float")?br:fi,minFilter:li,samples:4,stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:le.workingColorSpace}));const dt=p.state.transmissionRenderTarget[$.id],yt=$.viewport||F;dt.setSize(yt.z,yt.w);const Dt=y.getRenderTarget();y.setRenderTarget(dt),y.getClearColor(Z),tt=y.getClearAlpha(),tt<1&&y.setClearColor(16777215,.5),y.clear(),ue&&Xt.render(Y);const It=y.toneMapping;y.toneMapping=Li;const Kt=$.viewport;if($.viewport!==void 0&&($.viewport=void 0),p.setupLightsView($),J===!0&&ft.setGlobalState(y.clippingPlanes,$),ns(A,Y,$),U.updateMultisampleRenderTarget(dt),U.updateRenderTargetMipmap(dt),oe.has("WEBGL_multisampled_render_to_texture")===!1){let ee=!1;for(let Ut=0,pe=V.length;Ut<pe;Ut++){const be=V[Ut],Ee=be.object,Be=be.geometry,_e=be.material,Ot=be.group;if(_e.side===dn&&Ee.layers.test($.layers)){const Dn=_e.side;_e.side=fn,_e.needsUpdate=!0,Zs(Ee,Y,$,Be,_e,Ot),_e.side=Dn,_e.needsUpdate=!0,ee=!0}}ee===!0&&(U.updateMultisampleRenderTarget(dt),U.updateRenderTargetMipmap(dt))}y.setRenderTarget(Dt),y.setClearColor(Z,tt),Kt!==void 0&&($.viewport=Kt),y.toneMapping=It}function ns(A,V,Y){const $=V.isScene===!0?V.overrideMaterial:null;for(let B=0,dt=A.length;B<dt;B++){const yt=A[B],Dt=yt.object,It=yt.geometry,Kt=$===null?yt.material:$,ee=yt.group;Dt.layers.test(Y.layers)&&Zs(Dt,V,Y,It,Kt,ee)}}function Zs(A,V,Y,$,B,dt){A.onBeforeRender(y,V,Y,$,B,dt),A.modelViewMatrix.multiplyMatrices(Y.matrixWorldInverse,A.matrixWorld),A.normalMatrix.getNormalMatrix(A.modelViewMatrix),B.onBeforeRender(y,V,Y,$,A,dt),B.transparent===!0&&B.side===dn&&B.forceSinglePass===!1?(B.side=fn,B.needsUpdate=!0,y.renderBufferDirect(Y,V,$,B,A,dt),B.side=di,B.needsUpdate=!0,y.renderBufferDirect(Y,V,$,B,A,dt),B.side=dn):y.renderBufferDirect(Y,V,$,B,A,dt),A.onAfterRender(y,V,Y,$,B,dt)}function is(A,V,Y){V.isScene!==!0&&(V=Re);const $=Ht.get(A),B=p.state.lights,dt=p.state.shadowsArray,yt=B.state.version,Dt=Ft.getParameters(A,B.state,dt,V,Y),It=Ft.getProgramCacheKey(Dt);let Kt=$.programs;$.environment=A.isMeshStandardMaterial?V.environment:null,$.fog=V.fog,$.envMap=(A.isMeshStandardMaterial?j:S).get(A.envMap||$.environment),$.envMapRotation=$.environment!==null&&A.envMap===null?V.environmentRotation:A.envMapRotation,Kt===void 0&&(A.addEventListener("dispose",te),Kt=new Map,$.programs=Kt);let ee=Kt.get(It);if(ee!==void 0){if($.currentProgram===ee&&$.lightsStateVersion===yt)return Pr(A,Dt),ee}else Dt.uniforms=Ft.getUniforms(A),A.onBeforeCompile(Dt,y),ee=Ft.acquireProgram(Dt,It),Kt.set(It,ee),$.uniforms=Dt.uniforms;const Ut=$.uniforms;return(!A.isShaderMaterial&&!A.isRawShaderMaterial||A.clipping===!0)&&(Ut.clippingPlanes=ft.uniform),Pr(A,Dt),$.needsLights=eo(A),$.lightsStateVersion=yt,$.needsLights&&(Ut.ambientLightColor.value=B.state.ambient,Ut.lightProbe.value=B.state.probe,Ut.directionalLights.value=B.state.directional,Ut.directionalLightShadows.value=B.state.directionalShadow,Ut.spotLights.value=B.state.spot,Ut.spotLightShadows.value=B.state.spotShadow,Ut.rectAreaLights.value=B.state.rectArea,Ut.ltc_1.value=B.state.rectAreaLTC1,Ut.ltc_2.value=B.state.rectAreaLTC2,Ut.pointLights.value=B.state.point,Ut.pointLightShadows.value=B.state.pointShadow,Ut.hemisphereLights.value=B.state.hemi,Ut.directionalShadowMap.value=B.state.directionalShadowMap,Ut.directionalShadowMatrix.value=B.state.directionalShadowMatrix,Ut.spotShadowMap.value=B.state.spotShadowMap,Ut.spotLightMatrix.value=B.state.spotLightMatrix,Ut.spotLightMap.value=B.state.spotLightMap,Ut.pointShadowMap.value=B.state.pointShadowMap,Ut.pointShadowMatrix.value=B.state.pointShadowMatrix),$.currentProgram=ee,$.uniformsList=null,ee}function Rr(A){if(A.uniformsList===null){const V=A.currentProgram.getUniforms();A.uniformsList=xa.seqWithValue(V.seq,A.uniforms)}return A.uniformsList}function Pr(A,V){const Y=Ht.get(A);Y.outputColorSpace=V.outputColorSpace,Y.batching=V.batching,Y.batchingColor=V.batchingColor,Y.instancing=V.instancing,Y.instancingColor=V.instancingColor,Y.instancingMorph=V.instancingMorph,Y.skinning=V.skinning,Y.morphTargets=V.morphTargets,Y.morphNormals=V.morphNormals,Y.morphColors=V.morphColors,Y.morphTargetsCount=V.morphTargetsCount,Y.numClippingPlanes=V.numClippingPlanes,Y.numIntersection=V.numClipIntersection,Y.vertexAlphas=V.vertexAlphas,Y.vertexTangents=V.vertexTangents,Y.toneMapping=V.toneMapping}function Qa(A,V,Y,$,B){V.isScene!==!0&&(V=Re),U.resetTextureUnits();const dt=V.fog,yt=$.isMeshStandardMaterial?V.environment:null,Dt=I===null?y.outputColorSpace:I.isXRRenderTarget===!0?I.texture.colorSpace:Hs,It=($.isMeshStandardMaterial?j:S).get($.envMap||yt),Kt=$.vertexColors===!0&&!!Y.attributes.color&&Y.attributes.color.itemSize===4,ee=!!Y.attributes.tangent&&(!!$.normalMap||$.anisotropy>0),Ut=!!Y.morphAttributes.position,pe=!!Y.morphAttributes.normal,be=!!Y.morphAttributes.color;let Ee=Li;$.toneMapped&&(I===null||I.isXRRenderTarget===!0)&&(Ee=y.toneMapping);const Be=Y.morphAttributes.position||Y.morphAttributes.normal||Y.morphAttributes.color,_e=Be!==void 0?Be.length:0,Ot=Ht.get($),Dn=p.state.lights;if(J===!0&&(nt===!0||A!==b)){const nn=A===b&&$.id===M;ft.setState($,A,nn)}let me=!1;$.version===Ot.__version?(Ot.needsLights&&Ot.lightsStateVersion!==Dn.state.version||Ot.outputColorSpace!==Dt||B.isBatchedMesh&&Ot.batching===!1||!B.isBatchedMesh&&Ot.batching===!0||B.isBatchedMesh&&Ot.batchingColor===!0&&B.colorTexture===null||B.isBatchedMesh&&Ot.batchingColor===!1&&B.colorTexture!==null||B.isInstancedMesh&&Ot.instancing===!1||!B.isInstancedMesh&&Ot.instancing===!0||B.isSkinnedMesh&&Ot.skinning===!1||!B.isSkinnedMesh&&Ot.skinning===!0||B.isInstancedMesh&&Ot.instancingColor===!0&&B.instanceColor===null||B.isInstancedMesh&&Ot.instancingColor===!1&&B.instanceColor!==null||B.isInstancedMesh&&Ot.instancingMorph===!0&&B.morphTexture===null||B.isInstancedMesh&&Ot.instancingMorph===!1&&B.morphTexture!==null||Ot.envMap!==It||$.fog===!0&&Ot.fog!==dt||Ot.numClippingPlanes!==void 0&&(Ot.numClippingPlanes!==ft.numPlanes||Ot.numIntersection!==ft.numIntersection)||Ot.vertexAlphas!==Kt||Ot.vertexTangents!==ee||Ot.morphTargets!==Ut||Ot.morphNormals!==pe||Ot.morphColors!==be||Ot.toneMapping!==Ee||Ot.morphTargetsCount!==_e)&&(me=!0):(me=!0,Ot.__version=$.version);let gn=Ot.currentProgram;me===!0&&(gn=is($,V,B));let _i=!1,en=!1,vi=!1;const Zt=gn.getUniforms(),ln=Ot.uniforms;if(Wt.useProgram(gn.program)&&(_i=!0,en=!0,vi=!0),$.id!==M&&(M=$.id,en=!0),_i||b!==A){Wt.buffers.depth.getReversed()?(it.copy(A.projectionMatrix),Pf(it),Lf(it),Zt.setValue(G,"projectionMatrix",it)):Zt.setValue(G,"projectionMatrix",A.projectionMatrix),Zt.setValue(G,"viewMatrix",A.matrixWorldInverse);const In=Zt.map.cameraPosition;In!==void 0&&In.setValue(G,zt.setFromMatrixPosition(A.matrixWorld)),ce.logarithmicDepthBuffer&&Zt.setValue(G,"logDepthBufFC",2/(Math.log(A.far+1)/Math.LN2)),($.isMeshPhongMaterial||$.isMeshToonMaterial||$.isMeshLambertMaterial||$.isMeshBasicMaterial||$.isMeshStandardMaterial||$.isShaderMaterial)&&Zt.setValue(G,"isOrthographic",A.isOrthographicCamera===!0),b!==A&&(b=A,en=!0,vi=!0)}if(B.isSkinnedMesh){Zt.setOptional(G,B,"bindMatrix"),Zt.setOptional(G,B,"bindMatrixInverse");const nn=B.skeleton;nn&&(nn.boneTexture===null&&nn.computeBoneTexture(),Zt.setValue(G,"boneTexture",nn.boneTexture,U))}B.isBatchedMesh&&(Zt.setOptional(G,B,"batchingTexture"),Zt.setValue(G,"batchingTexture",B._matricesTexture,U),Zt.setOptional(G,B,"batchingIdTexture"),Zt.setValue(G,"batchingIdTexture",B._indirectTexture,U),Zt.setOptional(G,B,"batchingColorTexture"),B._colorsTexture!==null&&Zt.setValue(G,"batchingColorTexture",B._colorsTexture,U));const Oi=Y.morphAttributes;if((Oi.position!==void 0||Oi.normal!==void 0||Oi.color!==void 0)&&$t.update(B,Y,gn),(en||Ot.receiveShadow!==B.receiveShadow)&&(Ot.receiveShadow=B.receiveShadow,Zt.setValue(G,"receiveShadow",B.receiveShadow)),$.isMeshGouraudMaterial&&$.envMap!==null&&(ln.envMap.value=It,ln.flipEnvMap.value=It.isCubeTexture&&It.isRenderTargetTexture===!1?-1:1),$.isMeshStandardMaterial&&$.envMap===null&&V.environment!==null&&(ln.envMapIntensity.value=V.environmentIntensity),en&&(Zt.setValue(G,"toneMappingExposure",y.toneMappingExposure),Ot.needsLights&&to(ln,vi),dt&&$.fog===!0&&Mt.refreshFogUniforms(ln,dt),Mt.refreshMaterialUniforms(ln,$,W,et,p.state.transmissionRenderTarget[A.id]),xa.upload(G,Rr(Ot),ln,U)),$.isShaderMaterial&&$.uniformsNeedUpdate===!0&&(xa.upload(G,Rr(Ot),ln,U),$.uniformsNeedUpdate=!1),$.isSpriteMaterial&&Zt.setValue(G,"center",B.center),Zt.setValue(G,"modelViewMatrix",B.modelViewMatrix),Zt.setValue(G,"normalMatrix",B.normalMatrix),Zt.setValue(G,"modelMatrix",B.matrixWorld),$.isShaderMaterial||$.isRawShaderMaterial){const nn=$.uniformsGroups;for(let In=0,An=nn.length;In<An;In++){const ki=nn[In];z.update(ki,gn),z.bind(ki,gn)}}return gn}function to(A,V){A.ambientLightColor.needsUpdate=V,A.lightProbe.needsUpdate=V,A.directionalLights.needsUpdate=V,A.directionalLightShadows.needsUpdate=V,A.pointLights.needsUpdate=V,A.pointLightShadows.needsUpdate=V,A.spotLights.needsUpdate=V,A.spotLightShadows.needsUpdate=V,A.rectAreaLights.needsUpdate=V,A.hemisphereLights.needsUpdate=V}function eo(A){return A.isMeshLambertMaterial||A.isMeshToonMaterial||A.isMeshPhongMaterial||A.isMeshStandardMaterial||A.isShadowMaterial||A.isShaderMaterial&&A.lights===!0}this.getActiveCubeFace=function(){return C},this.getActiveMipmapLevel=function(){return L},this.getRenderTarget=function(){return I},this.setRenderTargetTextures=function(A,V,Y){Ht.get(A.texture).__webglTexture=V,Ht.get(A.depthTexture).__webglTexture=Y;const $=Ht.get(A);$.__hasExternalTextures=!0,$.__autoAllocateDepthBuffer=Y===void 0,$.__autoAllocateDepthBuffer||oe.has("WEBGL_multisampled_render_to_texture")===!0&&(console.warn("THREE.WebGLRenderer: Render-to-texture extension was disabled because an external texture was provided"),$.__useRenderToTexture=!1)},this.setRenderTargetFramebuffer=function(A,V){const Y=Ht.get(A);Y.__webglFramebuffer=V,Y.__useDefaultFramebuffer=V===void 0},this.setRenderTarget=function(A,V=0,Y=0){I=A,C=V,L=Y;let $=!0,B=null,dt=!1,yt=!1;if(A){const It=Ht.get(A);if(It.__useDefaultFramebuffer!==void 0)Wt.bindFramebuffer(G.FRAMEBUFFER,null),$=!1;else if(It.__webglFramebuffer===void 0)U.setupRenderTarget(A);else if(It.__hasExternalTextures)U.rebindTextures(A,Ht.get(A.texture).__webglTexture,Ht.get(A.depthTexture).__webglTexture);else if(A.depthBuffer){const Ut=A.depthTexture;if(It.__boundDepthTexture!==Ut){if(Ut!==null&&Ht.has(Ut)&&(A.width!==Ut.image.width||A.height!==Ut.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");U.setupDepthRenderbuffer(A)}}const Kt=A.texture;(Kt.isData3DTexture||Kt.isDataArrayTexture||Kt.isCompressedArrayTexture)&&(yt=!0);const ee=Ht.get(A).__webglFramebuffer;A.isWebGLCubeRenderTarget?(Array.isArray(ee[V])?B=ee[V][Y]:B=ee[V],dt=!0):A.samples>0&&U.useMultisampledRTT(A)===!1?B=Ht.get(A).__webglMultisampledFramebuffer:Array.isArray(ee)?B=ee[Y]:B=ee,F.copy(A.viewport),k.copy(A.scissor),H=A.scissorTest}else F.copy(mt).multiplyScalar(W).floor(),k.copy(Rt).multiplyScalar(W).floor(),H=wt;if(Wt.bindFramebuffer(G.FRAMEBUFFER,B)&&$&&Wt.drawBuffers(A,B),Wt.viewport(F),Wt.scissor(k),Wt.setScissorTest(H),dt){const It=Ht.get(A.texture);G.framebufferTexture2D(G.FRAMEBUFFER,G.COLOR_ATTACHMENT0,G.TEXTURE_CUBE_MAP_POSITIVE_X+V,It.__webglTexture,Y)}else if(yt){const It=Ht.get(A.texture),Kt=V||0;G.framebufferTextureLayer(G.FRAMEBUFFER,G.COLOR_ATTACHMENT0,It.__webglTexture,Y||0,Kt)}M=-1},this.readRenderTargetPixels=function(A,V,Y,$,B,dt,yt){if(!(A&&A.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let Dt=Ht.get(A).__webglFramebuffer;if(A.isWebGLCubeRenderTarget&&yt!==void 0&&(Dt=Dt[yt]),Dt){Wt.bindFramebuffer(G.FRAMEBUFFER,Dt);try{const It=A.texture,Kt=It.format,ee=It.type;if(!ce.textureFormatReadable(Kt)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!ce.textureTypeReadable(ee)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}V>=0&&V<=A.width-$&&Y>=0&&Y<=A.height-B&&G.readPixels(V,Y,$,B,ne.convert(Kt),ne.convert(ee),dt)}finally{const It=I!==null?Ht.get(I).__webglFramebuffer:null;Wt.bindFramebuffer(G.FRAMEBUFFER,It)}}},this.readRenderTargetPixelsAsync=async function(A,V,Y,$,B,dt,yt){if(!(A&&A.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let Dt=Ht.get(A).__webglFramebuffer;if(A.isWebGLCubeRenderTarget&&yt!==void 0&&(Dt=Dt[yt]),Dt){const It=A.texture,Kt=It.format,ee=It.type;if(!ce.textureFormatReadable(Kt))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!ce.textureTypeReadable(ee))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");if(V>=0&&V<=A.width-$&&Y>=0&&Y<=A.height-B){Wt.bindFramebuffer(G.FRAMEBUFFER,Dt);const Ut=G.createBuffer();G.bindBuffer(G.PIXEL_PACK_BUFFER,Ut),G.bufferData(G.PIXEL_PACK_BUFFER,dt.byteLength,G.STREAM_READ),G.readPixels(V,Y,$,B,ne.convert(Kt),ne.convert(ee),0);const pe=I!==null?Ht.get(I).__webglFramebuffer:null;Wt.bindFramebuffer(G.FRAMEBUFFER,pe);const be=G.fenceSync(G.SYNC_GPU_COMMANDS_COMPLETE,0);return G.flush(),await Rf(G,be,4),G.bindBuffer(G.PIXEL_PACK_BUFFER,Ut),G.getBufferSubData(G.PIXEL_PACK_BUFFER,0,dt),G.deleteBuffer(Ut),G.deleteSync(be),dt}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")}},this.copyFramebufferToTexture=function(A,V=null,Y=0){A.isTexture!==!0&&(rr("WebGLRenderer: copyFramebufferToTexture function signature has changed."),V=arguments[0]||null,A=arguments[1]);const $=Math.pow(2,-Y),B=Math.floor(A.image.width*$),dt=Math.floor(A.image.height*$),yt=V!==null?V.x:0,Dt=V!==null?V.y:0;U.setTexture2D(A,0),G.copyTexSubImage2D(G.TEXTURE_2D,Y,0,0,yt,Dt,B,dt),Wt.unbindTexture()},this.copyTextureToTexture=function(A,V,Y=null,$=null,B=0){A.isTexture!==!0&&(rr("WebGLRenderer: copyTextureToTexture function signature has changed."),$=arguments[0]||null,A=arguments[1],V=arguments[2],B=arguments[3]||0,Y=null);let dt,yt,Dt,It,Kt,ee,Ut,pe,be;const Ee=A.isCompressedTexture?A.mipmaps[B]:A.image;Y!==null?(dt=Y.max.x-Y.min.x,yt=Y.max.y-Y.min.y,Dt=Y.isBox3?Y.max.z-Y.min.z:1,It=Y.min.x,Kt=Y.min.y,ee=Y.isBox3?Y.min.z:0):(dt=Ee.width,yt=Ee.height,Dt=Ee.depth||1,It=0,Kt=0,ee=0),$!==null?(Ut=$.x,pe=$.y,be=$.z):(Ut=0,pe=0,be=0);const Be=ne.convert(V.format),_e=ne.convert(V.type);let Ot;V.isData3DTexture?(U.setTexture3D(V,0),Ot=G.TEXTURE_3D):V.isDataArrayTexture||V.isCompressedArrayTexture?(U.setTexture2DArray(V,0),Ot=G.TEXTURE_2D_ARRAY):(U.setTexture2D(V,0),Ot=G.TEXTURE_2D),G.pixelStorei(G.UNPACK_FLIP_Y_WEBGL,V.flipY),G.pixelStorei(G.UNPACK_PREMULTIPLY_ALPHA_WEBGL,V.premultiplyAlpha),G.pixelStorei(G.UNPACK_ALIGNMENT,V.unpackAlignment);const Dn=G.getParameter(G.UNPACK_ROW_LENGTH),me=G.getParameter(G.UNPACK_IMAGE_HEIGHT),gn=G.getParameter(G.UNPACK_SKIP_PIXELS),_i=G.getParameter(G.UNPACK_SKIP_ROWS),en=G.getParameter(G.UNPACK_SKIP_IMAGES);G.pixelStorei(G.UNPACK_ROW_LENGTH,Ee.width),G.pixelStorei(G.UNPACK_IMAGE_HEIGHT,Ee.height),G.pixelStorei(G.UNPACK_SKIP_PIXELS,It),G.pixelStorei(G.UNPACK_SKIP_ROWS,Kt),G.pixelStorei(G.UNPACK_SKIP_IMAGES,ee);const vi=A.isDataArrayTexture||A.isData3DTexture,Zt=V.isDataArrayTexture||V.isData3DTexture;if(A.isRenderTargetTexture||A.isDepthTexture){const ln=Ht.get(A),Oi=Ht.get(V),nn=Ht.get(ln.__renderTarget),In=Ht.get(Oi.__renderTarget);Wt.bindFramebuffer(G.READ_FRAMEBUFFER,nn.__webglFramebuffer),Wt.bindFramebuffer(G.DRAW_FRAMEBUFFER,In.__webglFramebuffer);for(let An=0;An<Dt;An++)vi&&G.framebufferTextureLayer(G.READ_FRAMEBUFFER,G.COLOR_ATTACHMENT0,Ht.get(A).__webglTexture,B,ee+An),A.isDepthTexture?(Zt&&G.framebufferTextureLayer(G.DRAW_FRAMEBUFFER,G.COLOR_ATTACHMENT0,Ht.get(V).__webglTexture,B,be+An),G.blitFramebuffer(It,Kt,dt,yt,Ut,pe,dt,yt,G.DEPTH_BUFFER_BIT,G.NEAREST)):Zt?G.copyTexSubImage3D(Ot,B,Ut,pe,be+An,It,Kt,dt,yt):G.copyTexSubImage2D(Ot,B,Ut,pe,be+An,It,Kt,dt,yt);Wt.bindFramebuffer(G.READ_FRAMEBUFFER,null),Wt.bindFramebuffer(G.DRAW_FRAMEBUFFER,null)}else Zt?A.isDataTexture||A.isData3DTexture?G.texSubImage3D(Ot,B,Ut,pe,be,dt,yt,Dt,Be,_e,Ee.data):V.isCompressedArrayTexture?G.compressedTexSubImage3D(Ot,B,Ut,pe,be,dt,yt,Dt,Be,Ee.data):G.texSubImage3D(Ot,B,Ut,pe,be,dt,yt,Dt,Be,_e,Ee):A.isDataTexture?G.texSubImage2D(G.TEXTURE_2D,B,Ut,pe,dt,yt,Be,_e,Ee.data):A.isCompressedTexture?G.compressedTexSubImage2D(G.TEXTURE_2D,B,Ut,pe,Ee.width,Ee.height,Be,Ee.data):G.texSubImage2D(G.TEXTURE_2D,B,Ut,pe,dt,yt,Be,_e,Ee);G.pixelStorei(G.UNPACK_ROW_LENGTH,Dn),G.pixelStorei(G.UNPACK_IMAGE_HEIGHT,me),G.pixelStorei(G.UNPACK_SKIP_PIXELS,gn),G.pixelStorei(G.UNPACK_SKIP_ROWS,_i),G.pixelStorei(G.UNPACK_SKIP_IMAGES,en),B===0&&V.generateMipmaps&&G.generateMipmap(Ot),Wt.unbindTexture()},this.copyTextureToTexture3D=function(A,V,Y=null,$=null,B=0){return A.isTexture!==!0&&(rr("WebGLRenderer: copyTextureToTexture3D function signature has changed."),Y=arguments[0]||null,$=arguments[1]||null,A=arguments[2],V=arguments[3],B=arguments[4]||0),rr('WebGLRenderer: copyTextureToTexture3D function has been deprecated. Use "copyTextureToTexture" instead.'),this.copyTextureToTexture(A,V,Y,$,B)},this.initRenderTarget=function(A){Ht.get(A).__webglFramebuffer===void 0&&U.setupRenderTarget(A)},this.initTexture=function(A){A.isCubeTexture?U.setTextureCube(A,0):A.isData3DTexture?U.setTexture3D(A,0):A.isDataArrayTexture||A.isCompressedArrayTexture?U.setTexture2DArray(A,0):U.setTexture2D(A,0),Wt.unbindTexture()},this.resetState=function(){C=0,L=0,I=null,Wt.reset(),Me.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return hi}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(t){this._outputColorSpace=t;const e=this.getContext();e.drawingBufferColorspace=le._getDrawingBufferColorSpace(t),e.unpackColorSpace=le._getUnpackColorSpace()}}class Jc{constructor(t,e=1,n=1e3){this.isFog=!0,this.name="",this.color=new Jt(t),this.near=e,this.far=n}clone(){return new Jc(this.color,this.near,this.far)}toJSON(){return{type:"Fog",name:this.name,color:this.color.getHex(),near:this.near,far:this.far}}}class Lu extends De{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new pn,this.environmentIntensity=1,this.environmentRotation=new pn,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(t,e){return super.copy(t,e),t.background!==null&&(this.background=t.background.clone()),t.environment!==null&&(this.environment=t.environment.clone()),t.fog!==null&&(this.fog=t.fog.clone()),this.backgroundBlurriness=t.backgroundBlurriness,this.backgroundIntensity=t.backgroundIntensity,this.backgroundRotation.copy(t.backgroundRotation),this.environmentIntensity=t.environmentIntensity,this.environmentRotation.copy(t.environmentRotation),t.overrideMaterial!==null&&(this.overrideMaterial=t.overrideMaterial.clone()),this.matrixAutoUpdate=t.matrixAutoUpdate,this}toJSON(t){const e=super.toJSON(t);return this.fog!==null&&(e.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(e.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(e.object.backgroundIntensity=this.backgroundIntensity),e.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(e.object.environmentIntensity=this.environmentIntensity),e.object.environmentRotation=this.environmentRotation.toArray(),e}}const _h=new D,vh=new ye,xh=new ye,V0=new D,yh=new Yt,ta=new D,No=new gi,Mh=new Yt,Do=new Gs;class H0 extends ge{constructor(t,e){super(t,e),this.isSkinnedMesh=!0,this.type="SkinnedMesh",this.bindMode=vl,this.bindMatrix=new Yt,this.bindMatrixInverse=new Yt,this.boundingBox=null,this.boundingSphere=null}computeBoundingBox(){const t=this.geometry;this.boundingBox===null&&(this.boundingBox=new Gn),this.boundingBox.makeEmpty();const e=t.getAttribute("position");for(let n=0;n<e.count;n++)this.getVertexPosition(n,ta),this.boundingBox.expandByPoint(ta)}computeBoundingSphere(){const t=this.geometry;this.boundingSphere===null&&(this.boundingSphere=new gi),this.boundingSphere.makeEmpty();const e=t.getAttribute("position");for(let n=0;n<e.count;n++)this.getVertexPosition(n,ta),this.boundingSphere.expandByPoint(ta)}copy(t,e){return super.copy(t,e),this.bindMode=t.bindMode,this.bindMatrix.copy(t.bindMatrix),this.bindMatrixInverse.copy(t.bindMatrixInverse),this.skeleton=t.skeleton,t.boundingBox!==null&&(this.boundingBox=t.boundingBox.clone()),t.boundingSphere!==null&&(this.boundingSphere=t.boundingSphere.clone()),this}raycast(t,e){const n=this.material,s=this.matrixWorld;n!==void 0&&(this.boundingSphere===null&&this.computeBoundingSphere(),No.copy(this.boundingSphere),No.applyMatrix4(s),t.ray.intersectsSphere(No)!==!1&&(Mh.copy(s).invert(),Do.copy(t.ray).applyMatrix4(Mh),!(this.boundingBox!==null&&Do.intersectsBox(this.boundingBox)===!1)&&this._computeIntersections(t,e,Do)))}getVertexPosition(t,e){return super.getVertexPosition(t,e),this.applyBoneTransform(t,e),e}bind(t,e){this.skeleton=t,e===void 0&&(this.updateMatrixWorld(!0),this.skeleton.calculateInverses(),e=this.matrixWorld),this.bindMatrix.copy(e),this.bindMatrixInverse.copy(e).invert()}pose(){this.skeleton.pose()}normalizeSkinWeights(){const t=new ye,e=this.geometry.attributes.skinWeight;for(let n=0,s=e.count;n<s;n++){t.fromBufferAttribute(e,n);const r=1/t.manhattanLength();r!==1/0?t.multiplyScalar(r):t.set(1,0,0,0),e.setXYZW(n,t.x,t.y,t.z,t.w)}}updateMatrixWorld(t){super.updateMatrixWorld(t),this.bindMode===vl?this.bindMatrixInverse.copy(this.matrixWorld).invert():this.bindMode===Zd?this.bindMatrixInverse.copy(this.bindMatrix).invert():console.warn("THREE.SkinnedMesh: Unrecognized bindMode: "+this.bindMode)}applyBoneTransform(t,e){const n=this.skeleton,s=this.geometry;vh.fromBufferAttribute(s.attributes.skinIndex,t),xh.fromBufferAttribute(s.attributes.skinWeight,t),_h.copy(e).applyMatrix4(this.bindMatrix),e.set(0,0,0);for(let r=0;r<4;r++){const a=xh.getComponent(r);if(a!==0){const o=vh.getComponent(r);yh.multiplyMatrices(n.bones[o].matrixWorld,n.boneInverses[o]),e.addScaledVector(V0.copy(_h).applyMatrix4(yh),a)}}return e.applyMatrix4(this.bindMatrixInverse)}}class Nu extends De{constructor(){super(),this.isBone=!0,this.type="Bone"}}class Du extends Je{constructor(t=null,e=1,n=1,s,r,a,o,c,l=Mn,h=Mn,u,d){super(null,a,o,c,l,h,s,r,u,d),this.isDataTexture=!0,this.image={data:t,width:e,height:n},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}}const bh=new Yt,G0=new Yt;class Zc{constructor(t=[],e=[]){this.uuid=Fi(),this.bones=t.slice(0),this.boneInverses=e,this.boneMatrices=null,this.boneTexture=null,this.init()}init(){const t=this.bones,e=this.boneInverses;if(this.boneMatrices=new Float32Array(t.length*16),e.length===0)this.calculateInverses();else if(t.length!==e.length){console.warn("THREE.Skeleton: Number of inverse bone matrices does not match amount of bones."),this.boneInverses=[];for(let n=0,s=this.bones.length;n<s;n++)this.boneInverses.push(new Yt)}}calculateInverses(){this.boneInverses.length=0;for(let t=0,e=this.bones.length;t<e;t++){const n=new Yt;this.bones[t]&&n.copy(this.bones[t].matrixWorld).invert(),this.boneInverses.push(n)}}pose(){for(let t=0,e=this.bones.length;t<e;t++){const n=this.bones[t];n&&n.matrixWorld.copy(this.boneInverses[t]).invert()}for(let t=0,e=this.bones.length;t<e;t++){const n=this.bones[t];n&&(n.parent&&n.parent.isBone?(n.matrix.copy(n.parent.matrixWorld).invert(),n.matrix.multiply(n.matrixWorld)):n.matrix.copy(n.matrixWorld),n.matrix.decompose(n.position,n.quaternion,n.scale))}}update(){const t=this.bones,e=this.boneInverses,n=this.boneMatrices,s=this.boneTexture;for(let r=0,a=t.length;r<a;r++){const o=t[r]?t[r].matrixWorld:G0;bh.multiplyMatrices(o,e[r]),bh.toArray(n,r*16)}s!==null&&(s.needsUpdate=!0)}clone(){return new Zc(this.bones,this.boneInverses)}computeBoneTexture(){let t=Math.sqrt(this.bones.length*4);t=Math.ceil(t/4)*4,t=Math.max(t,4);const e=new Float32Array(t*t*4);e.set(this.boneMatrices);const n=new Du(e,t,t,Pn,qn);return n.needsUpdate=!0,this.boneMatrices=e,this.boneTexture=n,this}getBoneByName(t){for(let e=0,n=this.bones.length;e<n;e++){const s=this.bones[e];if(s.name===t)return s}}dispose(){this.boneTexture!==null&&(this.boneTexture.dispose(),this.boneTexture=null)}fromJSON(t,e){this.uuid=t.uuid;for(let n=0,s=t.bones.length;n<s;n++){const r=t.bones[n];let a=e[r];a===void 0&&(console.warn("THREE.Skeleton: No bone found with UUID:",r),a=new Nu),this.bones.push(a),this.boneInverses.push(new Yt().fromArray(t.boneInverses[n]))}return this.init(),this}toJSON(){const t={metadata:{version:4.6,type:"Skeleton",generator:"Skeleton.toJSON"},bones:[],boneInverses:[]};t.uuid=this.uuid;const e=this.bones,n=this.boneInverses;for(let s=0,r=e.length;s<r;s++){const a=e[s];t.bones.push(a.uuid);const o=n[s];t.boneInverses.push(o.toArray())}return t}}class zn extends Hn{static get type(){return"LineBasicMaterial"}constructor(t){super(),this.isLineBasicMaterial=!0,this.color=new Jt(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.linewidth=t.linewidth,this.linecap=t.linecap,this.linejoin=t.linejoin,this.fog=t.fog,this}}const Ea=new D,wa=new D,Sh=new Yt,ir=new Gs,ea=new gi,Io=new D,Eh=new D;class qs extends De{constructor(t=new Le,e=new zn){super(),this.isLine=!0,this.type="Line",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[0];for(let s=1,r=e.count;s<r;s++)Ea.fromBufferAttribute(e,s-1),wa.fromBufferAttribute(e,s),n[s]=n[s-1],n[s]+=Ea.distanceTo(wa);t.setAttribute("lineDistance",new ie(n,1))}else console.warn("THREE.Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}raycast(t,e){const n=this.geometry,s=this.matrixWorld,r=t.params.Line.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),ea.copy(n.boundingSphere),ea.applyMatrix4(s),ea.radius+=r,t.ray.intersectsSphere(ea)===!1)return;Sh.copy(s).invert(),ir.copy(t.ray).applyMatrix4(Sh);const o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=this.isLineSegments?2:1,h=n.index,d=n.attributes.position;if(h!==null){const f=Math.max(0,a.start),g=Math.min(h.count,a.start+a.count);for(let _=f,m=g-1;_<m;_+=l){const p=h.getX(_),P=h.getX(_+1),w=na(this,t,ir,c,p,P);w&&e.push(w)}if(this.isLineLoop){const _=h.getX(g-1),m=h.getX(f),p=na(this,t,ir,c,_,m);p&&e.push(p)}}else{const f=Math.max(0,a.start),g=Math.min(d.count,a.start+a.count);for(let _=f,m=g-1;_<m;_+=l){const p=na(this,t,ir,c,_,_+1);p&&e.push(p)}if(this.isLineLoop){const _=na(this,t,ir,c,g-1,f);_&&e.push(_)}}}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}}function na(i,t,e,n,s,r){const a=i.geometry.attributes.position;if(Ea.fromBufferAttribute(a,s),wa.fromBufferAttribute(a,r),e.distanceSqToSegment(Ea,wa,Io,Eh)>n)return;Io.applyMatrix4(i.matrixWorld);const c=t.ray.origin.distanceTo(Io);if(!(c<t.near||c>t.far))return{distance:c,point:Eh.clone().applyMatrix4(i.matrixWorld),index:s,face:null,faceIndex:null,barycoord:null,object:i}}const wh=new D,Th=new D;class Ta extends qs{constructor(t,e){super(t,e),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){const t=this.geometry;if(t.index===null){const e=t.attributes.position,n=[];for(let s=0,r=e.count;s<r;s+=2)wh.fromBufferAttribute(e,s),Th.fromBufferAttribute(e,s+1),n[s]=s===0?0:n[s-1],n[s+1]=n[s]+wh.distanceTo(Th);t.setAttribute("lineDistance",new ie(n,1))}else console.warn("THREE.LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}}class or extends Hn{static get type(){return"PointsMaterial"}constructor(t){super(),this.isPointsMaterial=!0,this.color=new Jt(16777215),this.map=null,this.alphaMap=null,this.size=1,this.sizeAttenuation=!0,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.alphaMap=t.alphaMap,this.size=t.size,this.sizeAttenuation=t.sizeAttenuation,this.fog=t.fog,this}}const Ah=new Yt,Ic=new Gs,ia=new gi,sa=new D;class Uo extends De{constructor(t=new Le,e=new or){super(),this.isPoints=!0,this.type="Points",this.geometry=t,this.material=e,this.updateMorphTargets()}copy(t,e){return super.copy(t,e),this.material=Array.isArray(t.material)?t.material.slice():t.material,this.geometry=t.geometry,this}raycast(t,e){const n=this.geometry,s=this.matrixWorld,r=t.params.Points.threshold,a=n.drawRange;if(n.boundingSphere===null&&n.computeBoundingSphere(),ia.copy(n.boundingSphere),ia.applyMatrix4(s),ia.radius+=r,t.ray.intersectsSphere(ia)===!1)return;Ah.copy(s).invert(),Ic.copy(t.ray).applyMatrix4(Ah);const o=r/((this.scale.x+this.scale.y+this.scale.z)/3),c=o*o,l=n.index,u=n.attributes.position;if(l!==null){const d=Math.max(0,a.start),f=Math.min(l.count,a.start+a.count);for(let g=d,_=f;g<_;g++){const m=l.getX(g);sa.fromBufferAttribute(u,m),Ch(sa,m,c,s,t,e,this)}}else{const d=Math.max(0,a.start),f=Math.min(u.count,a.start+a.count);for(let g=d,_=f;g<_;g++)sa.fromBufferAttribute(u,g),Ch(sa,g,c,s,t,e,this)}}updateMorphTargets(){const e=this.geometry.morphAttributes,n=Object.keys(e);if(n.length>0){const s=e[n[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){const o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}}function Ch(i,t,e,n,s,r,a){const o=Ic.distanceSqToPoint(i);if(o<e){const c=new D;Ic.closestPointToPoint(i,c),c.applyMatrix4(n);const l=s.ray.origin.distanceTo(c);if(l<s.near||l>s.far)return;r.push({distance:l,distanceToRay:Math.sqrt(o),point:c,index:t,face:null,faceIndex:null,barycoord:null,object:a})}}class Kn{constructor(){this.type="Curve",this.arcLengthDivisions=200}getPoint(){return console.warn("THREE.Curve: .getPoint() not implemented."),null}getPointAt(t,e){const n=this.getUtoTmapping(t);return this.getPoint(n,e)}getPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return e}getSpacedPoints(t=5){const e=[];for(let n=0;n<=t;n++)e.push(this.getPointAt(n/t));return e}getLength(){const t=this.getLengths();return t[t.length-1]}getLengths(t=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===t+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;const e=[];let n,s=this.getPoint(0),r=0;e.push(0);for(let a=1;a<=t;a++)n=this.getPoint(a/t),r+=n.distanceTo(s),e.push(r),s=n;return this.cacheArcLengths=e,e}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(t,e){const n=this.getLengths();let s=0;const r=n.length;let a;e?a=e:a=t*n[r-1];let o=0,c=r-1,l;for(;o<=c;)if(s=Math.floor(o+(c-o)/2),l=n[s]-a,l<0)o=s+1;else if(l>0)c=s-1;else{c=s;break}if(s=c,n[s]===a)return s/(r-1);const h=n[s],d=n[s+1]-h,f=(a-h)/d;return(s+f)/(r-1)}getTangent(t,e){let s=t-1e-4,r=t+1e-4;s<0&&(s=0),r>1&&(r=1);const a=this.getPoint(s),o=this.getPoint(r),c=e||(a.isVector2?new At:new D);return c.copy(o).sub(a).normalize(),c}getTangentAt(t,e){const n=this.getUtoTmapping(t);return this.getTangent(n,e)}computeFrenetFrames(t,e){const n=new D,s=[],r=[],a=[],o=new D,c=new Yt;for(let f=0;f<=t;f++){const g=f/t;s[f]=this.getTangentAt(g,new D)}r[0]=new D,a[0]=new D;let l=Number.MAX_VALUE;const h=Math.abs(s[0].x),u=Math.abs(s[0].y),d=Math.abs(s[0].z);h<=l&&(l=h,n.set(1,0,0)),u<=l&&(l=u,n.set(0,1,0)),d<=l&&n.set(0,0,1),o.crossVectors(s[0],n).normalize(),r[0].crossVectors(s[0],o),a[0].crossVectors(s[0],r[0]);for(let f=1;f<=t;f++){if(r[f]=r[f-1].clone(),a[f]=a[f-1].clone(),o.crossVectors(s[f-1],s[f]),o.length()>Number.EPSILON){o.normalize();const g=Math.acos(Ye(s[f-1].dot(s[f]),-1,1));r[f].applyMatrix4(c.makeRotationAxis(o,g))}a[f].crossVectors(s[f],r[f])}if(e===!0){let f=Math.acos(Ye(r[0].dot(r[t]),-1,1));f/=t,s[0].dot(o.crossVectors(r[0],r[t]))>0&&(f=-f);for(let g=1;g<=t;g++)r[g].applyMatrix4(c.makeRotationAxis(s[g],f*g)),a[g].crossVectors(s[g],r[g])}return{tangents:s,normals:r,binormals:a}}clone(){return new this.constructor().copy(this)}copy(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}toJSON(){const t={metadata:{version:4.6,type:"Curve",generator:"Curve.toJSON"}};return t.arcLengthDivisions=this.arcLengthDivisions,t.type=this.type,t}fromJSON(t){return this.arcLengthDivisions=t.arcLengthDivisions,this}}class Iu extends Kn{constructor(t=0,e=0,n=1,s=1,r=0,a=Math.PI*2,o=!1,c=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=t,this.aY=e,this.xRadius=n,this.yRadius=s,this.aStartAngle=r,this.aEndAngle=a,this.aClockwise=o,this.aRotation=c}getPoint(t,e=new At){const n=e,s=Math.PI*2;let r=this.aEndAngle-this.aStartAngle;const a=Math.abs(r)<Number.EPSILON;for(;r<0;)r+=s;for(;r>s;)r-=s;r<Number.EPSILON&&(a?r=0:r=s),this.aClockwise===!0&&!a&&(r===s?r=-s:r=r-s);const o=this.aStartAngle+t*r;let c=this.aX+this.xRadius*Math.cos(o),l=this.aY+this.yRadius*Math.sin(o);if(this.aRotation!==0){const h=Math.cos(this.aRotation),u=Math.sin(this.aRotation),d=c-this.aX,f=l-this.aY;c=d*h-f*u+this.aX,l=d*u+f*h+this.aY}return n.set(c,l)}copy(t){return super.copy(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}toJSON(){const t=super.toJSON();return t.aX=this.aX,t.aY=this.aY,t.xRadius=this.xRadius,t.yRadius=this.yRadius,t.aStartAngle=this.aStartAngle,t.aEndAngle=this.aEndAngle,t.aClockwise=this.aClockwise,t.aRotation=this.aRotation,t}fromJSON(t){return super.fromJSON(t),this.aX=t.aX,this.aY=t.aY,this.xRadius=t.xRadius,this.yRadius=t.yRadius,this.aStartAngle=t.aStartAngle,this.aEndAngle=t.aEndAngle,this.aClockwise=t.aClockwise,this.aRotation=t.aRotation,this}}class W0 extends Iu{constructor(t,e,n,s,r,a){super(t,e,n,n,s,r,a),this.isArcCurve=!0,this.type="ArcCurve"}}function Qc(){let i=0,t=0,e=0,n=0;function s(r,a,o,c){i=r,t=o,e=-3*r+3*a-2*o-c,n=2*r-2*a+o+c}return{initCatmullRom:function(r,a,o,c,l){s(a,o,l*(o-r),l*(c-a))},initNonuniformCatmullRom:function(r,a,o,c,l,h,u){let d=(a-r)/l-(o-r)/(l+h)+(o-a)/h,f=(o-a)/h-(c-a)/(h+u)+(c-o)/u;d*=h,f*=h,s(a,o,d,f)},calc:function(r){const a=r*r,o=a*r;return i+t*r+e*a+n*o}}}const ra=new D,Fo=new Qc,Oo=new Qc,ko=new Qc;class X0 extends Kn{constructor(t=[],e=!1,n="centripetal",s=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=t,this.closed=e,this.curveType=n,this.tension=s}getPoint(t,e=new D){const n=e,s=this.points,r=s.length,a=(r-(this.closed?0:1))*t;let o=Math.floor(a),c=a-o;this.closed?o+=o>0?0:(Math.floor(Math.abs(o)/r)+1)*r:c===0&&o===r-1&&(o=r-2,c=1);let l,h;this.closed||o>0?l=s[(o-1)%r]:(ra.subVectors(s[0],s[1]).add(s[0]),l=ra);const u=s[o%r],d=s[(o+1)%r];if(this.closed||o+2<r?h=s[(o+2)%r]:(ra.subVectors(s[r-1],s[r-2]).add(s[r-1]),h=ra),this.curveType==="centripetal"||this.curveType==="chordal"){const f=this.curveType==="chordal"?.5:.25;let g=Math.pow(l.distanceToSquared(u),f),_=Math.pow(u.distanceToSquared(d),f),m=Math.pow(d.distanceToSquared(h),f);_<1e-4&&(_=1),g<1e-4&&(g=_),m<1e-4&&(m=_),Fo.initNonuniformCatmullRom(l.x,u.x,d.x,h.x,g,_,m),Oo.initNonuniformCatmullRom(l.y,u.y,d.y,h.y,g,_,m),ko.initNonuniformCatmullRom(l.z,u.z,d.z,h.z,g,_,m)}else this.curveType==="catmullrom"&&(Fo.initCatmullRom(l.x,u.x,d.x,h.x,this.tension),Oo.initCatmullRom(l.y,u.y,d.y,h.y,this.tension),ko.initCatmullRom(l.z,u.z,d.z,h.z,this.tension));return n.set(Fo.calc(c),Oo.calc(c),ko.calc(c)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(s.clone())}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const s=this.points[e];t.points.push(s.toArray())}return t.closed=this.closed,t.curveType=this.curveType,t.tension=this.tension,t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(new D().fromArray(s))}return this.closed=t.closed,this.curveType=t.curveType,this.tension=t.tension,this}}function Rh(i,t,e,n,s){const r=(n-t)*.5,a=(s-e)*.5,o=i*i,c=i*o;return(2*e-2*n+r+a)*c+(-3*e+3*n-2*r-a)*o+r*i+e}function q0(i,t){const e=1-i;return e*e*t}function j0(i,t){return 2*(1-i)*i*t}function Y0(i,t){return i*i*t}function ur(i,t,e,n){return q0(i,t)+j0(i,e)+Y0(i,n)}function $0(i,t){const e=1-i;return e*e*e*t}function K0(i,t){const e=1-i;return 3*e*e*i*t}function J0(i,t){return 3*(1-i)*i*i*t}function Z0(i,t){return i*i*i*t}function dr(i,t,e,n,s){return $0(i,t)+K0(i,e)+J0(i,n)+Z0(i,s)}class Q0 extends Kn{constructor(t=new At,e=new At,n=new At,s=new At){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=t,this.v1=e,this.v2=n,this.v3=s}getPoint(t,e=new At){const n=e,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(dr(t,s.x,r.x,a.x,o.x),dr(t,s.y,r.y,a.y,o.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class tv extends Kn{constructor(t=new D,e=new D,n=new D,s=new D){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=t,this.v1=e,this.v2=n,this.v3=s}getPoint(t,e=new D){const n=e,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return n.set(dr(t,s.x,r.x,a.x,o.x),dr(t,s.y,r.y,a.y,o.y),dr(t,s.z,r.z,a.z,o.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this.v3.copy(t.v3),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t.v3=this.v3.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this.v3.fromArray(t.v3),this}}class ev extends Kn{constructor(t=new At,e=new At){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=t,this.v2=e}getPoint(t,e=new At){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new At){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class Uu extends Kn{constructor(t=new D,e=new D){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=t,this.v2=e}getPoint(t,e=new D){const n=e;return t===1?n.copy(this.v2):(n.copy(this.v2).sub(this.v1),n.multiplyScalar(t).add(this.v1)),n}getPointAt(t,e){return this.getPoint(t,e)}getTangent(t,e=new D){return e.subVectors(this.v2,this.v1).normalize()}getTangentAt(t,e){return this.getTangent(t,e)}copy(t){return super.copy(t),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class nv extends Kn{constructor(t=new At,e=new At,n=new At){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new At){const n=e,s=this.v0,r=this.v1,a=this.v2;return n.set(ur(t,s.x,r.x,a.x),ur(t,s.y,r.y,a.y)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class Fu extends Kn{constructor(t=new D,e=new D,n=new D){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=t,this.v1=e,this.v2=n}getPoint(t,e=new D){const n=e,s=this.v0,r=this.v1,a=this.v2;return n.set(ur(t,s.x,r.x,a.x),ur(t,s.y,r.y,a.y),ur(t,s.z,r.z,a.z)),n}copy(t){return super.copy(t),this.v0.copy(t.v0),this.v1.copy(t.v1),this.v2.copy(t.v2),this}toJSON(){const t=super.toJSON();return t.v0=this.v0.toArray(),t.v1=this.v1.toArray(),t.v2=this.v2.toArray(),t}fromJSON(t){return super.fromJSON(t),this.v0.fromArray(t.v0),this.v1.fromArray(t.v1),this.v2.fromArray(t.v2),this}}class iv extends Kn{constructor(t=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=t}getPoint(t,e=new At){const n=e,s=this.points,r=(s.length-1)*t,a=Math.floor(r),o=r-a,c=s[a===0?a:a-1],l=s[a],h=s[a>s.length-2?s.length-1:a+1],u=s[a>s.length-3?s.length-1:a+2];return n.set(Rh(o,c.x,l.x,h.x,u.x),Rh(o,c.y,l.y,h.y,u.y)),n}copy(t){super.copy(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(s.clone())}return this}toJSON(){const t=super.toJSON();t.points=[];for(let e=0,n=this.points.length;e<n;e++){const s=this.points[e];t.points.push(s.toArray())}return t}fromJSON(t){super.fromJSON(t),this.points=[];for(let e=0,n=t.points.length;e<n;e++){const s=t.points[e];this.points.push(new At().fromArray(s))}return this}}var Uc=Object.freeze({__proto__:null,ArcCurve:W0,CatmullRomCurve3:X0,CubicBezierCurve:Q0,CubicBezierCurve3:tv,EllipseCurve:Iu,LineCurve:ev,LineCurve3:Uu,QuadraticBezierCurve:nv,QuadraticBezierCurve3:Fu,SplineCurve:iv});class sv extends Kn{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(t){this.curves.push(t)}closePath(){const t=this.curves[0].getPoint(0),e=this.curves[this.curves.length-1].getPoint(1);if(!t.equals(e)){const n=t.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new Uc[n](e,t))}return this}getPoint(t,e){const n=t*this.getLength(),s=this.getCurveLengths();let r=0;for(;r<s.length;){if(s[r]>=n){const a=s[r]-n,o=this.curves[r],c=o.getLength(),l=c===0?0:1-a/c;return o.getPointAt(l,e)}r++}return null}getLength(){const t=this.getCurveLengths();return t[t.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;const t=[];let e=0;for(let n=0,s=this.curves.length;n<s;n++)e+=this.curves[n].getLength(),t.push(e);return this.cacheLengths=t,t}getSpacedPoints(t=40){const e=[];for(let n=0;n<=t;n++)e.push(this.getPoint(n/t));return this.autoClose&&e.push(e[0]),e}getPoints(t=12){const e=[];let n;for(let s=0,r=this.curves;s<r.length;s++){const a=r[s],o=a.isEllipseCurve?t*2:a.isLineCurve||a.isLineCurve3?1:a.isSplineCurve?t*a.points.length:t,c=a.getPoints(o);for(let l=0;l<c.length;l++){const h=c[l];n&&n.equals(h)||(e.push(h),n=h)}}return this.autoClose&&e.length>1&&!e[e.length-1].equals(e[0])&&e.push(e[0]),e}copy(t){super.copy(t),this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const s=t.curves[e];this.curves.push(s.clone())}return this.autoClose=t.autoClose,this}toJSON(){const t=super.toJSON();t.autoClose=this.autoClose,t.curves=[];for(let e=0,n=this.curves.length;e<n;e++){const s=this.curves[e];t.curves.push(s.toJSON())}return t}fromJSON(t){super.fromJSON(t),this.autoClose=t.autoClose,this.curves=[];for(let e=0,n=t.curves.length;e<n;e++){const s=t.curves[e];this.curves.push(new Uc[s.type]().fromJSON(s))}return this}}class Aa extends Le{constructor(t=1,e=32,n=0,s=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius:t,segments:e,thetaStart:n,thetaLength:s},e=Math.max(3,e);const r=[],a=[],o=[],c=[],l=new D,h=new At;a.push(0,0,0),o.push(0,0,1),c.push(.5,.5);for(let u=0,d=3;u<=e;u++,d+=3){const f=n+u/e*s;l.x=t*Math.cos(f),l.y=t*Math.sin(f),a.push(l.x,l.y,l.z),o.push(0,0,1),h.x=(a[d]/t+1)/2,h.y=(a[d+1]/t+1)/2,c.push(h.x,h.y)}for(let u=1;u<=e;u++)r.push(u,u+1,0);this.setIndex(r),this.setAttribute("position",new ie(a,3)),this.setAttribute("normal",new ie(o,3)),this.setAttribute("uv",new ie(c,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Aa(t.radius,t.segments,t.thetaStart,t.thetaLength)}}class js extends Le{constructor(t=1,e=1,n=1,s=32,r=1,a=!1,o=0,c=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop:t,radiusBottom:e,height:n,radialSegments:s,heightSegments:r,openEnded:a,thetaStart:o,thetaLength:c};const l=this;s=Math.floor(s),r=Math.floor(r);const h=[],u=[],d=[],f=[];let g=0;const _=[],m=n/2;let p=0;P(),a===!1&&(t>0&&w(!0),e>0&&w(!1)),this.setIndex(h),this.setAttribute("position",new ie(u,3)),this.setAttribute("normal",new ie(d,3)),this.setAttribute("uv",new ie(f,2));function P(){const y=new D,N=new D;let C=0;const L=(e-t)/n;for(let I=0;I<=r;I++){const M=[],b=I/r,F=b*(e-t)+t;for(let k=0;k<=s;k++){const H=k/s,Z=H*c+o,tt=Math.sin(Z),O=Math.cos(Z);N.x=F*tt,N.y=-b*n+m,N.z=F*O,u.push(N.x,N.y,N.z),y.set(tt,L,O).normalize(),d.push(y.x,y.y,y.z),f.push(H,1-b),M.push(g++)}_.push(M)}for(let I=0;I<s;I++)for(let M=0;M<r;M++){const b=_[M][I],F=_[M+1][I],k=_[M+1][I+1],H=_[M][I+1];(t>0||M!==0)&&(h.push(b,F,H),C+=3),(e>0||M!==r-1)&&(h.push(F,k,H),C+=3)}l.addGroup(p,C,0),p+=C}function w(y){const N=g,C=new At,L=new D;let I=0;const M=y===!0?t:e,b=y===!0?1:-1;for(let k=1;k<=s;k++)u.push(0,m*b,0),d.push(0,b,0),f.push(.5,.5),g++;const F=g;for(let k=0;k<=s;k++){const Z=k/s*c+o,tt=Math.cos(Z),O=Math.sin(Z);L.x=M*O,L.y=m*b,L.z=M*tt,u.push(L.x,L.y,L.z),d.push(0,b,0),C.x=tt*.5+.5,C.y=O*.5*b+.5,f.push(C.x,C.y),g++}for(let k=0;k<s;k++){const H=N+k,Z=F+k;y===!0?h.push(Z,Z+1,H):h.push(Z+1,Z,H),I+=3}l.addGroup(p,I,y===!0?1:2),p+=I}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new js(t.radiusTop,t.radiusBottom,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class tl extends js{constructor(t=1,e=1,n=32,s=1,r=!1,a=0,o=Math.PI*2){super(0,t,e,n,s,r,a,o),this.type="ConeGeometry",this.parameters={radius:t,height:e,radialSegments:n,heightSegments:s,openEnded:r,thetaStart:a,thetaLength:o}}static fromJSON(t){return new tl(t.radius,t.height,t.radialSegments,t.heightSegments,t.openEnded,t.thetaStart,t.thetaLength)}}class Ca extends Le{constructor(t=.5,e=1,n=32,s=1,r=0,a=Math.PI*2){super(),this.type="RingGeometry",this.parameters={innerRadius:t,outerRadius:e,thetaSegments:n,phiSegments:s,thetaStart:r,thetaLength:a},n=Math.max(3,n),s=Math.max(1,s);const o=[],c=[],l=[],h=[];let u=t;const d=(e-t)/s,f=new D,g=new At;for(let _=0;_<=s;_++){for(let m=0;m<=n;m++){const p=r+m/n*a;f.x=u*Math.cos(p),f.y=u*Math.sin(p),c.push(f.x,f.y,f.z),l.push(0,0,1),g.x=(f.x/e+1)/2,g.y=(f.y/e+1)/2,h.push(g.x,g.y)}u+=d}for(let _=0;_<s;_++){const m=_*(n+1);for(let p=0;p<n;p++){const P=p+m,w=P,y=P+n+1,N=P+n+2,C=P+1;o.push(w,y,C),o.push(y,N,C)}}this.setIndex(o),this.setAttribute("position",new ie(c,3)),this.setAttribute("normal",new ie(l,3)),this.setAttribute("uv",new ie(h,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new Ca(t.innerRadius,t.outerRadius,t.thetaSegments,t.phiSegments,t.thetaStart,t.thetaLength)}}class pi extends Le{constructor(t=1,e=32,n=16,s=0,r=Math.PI*2,a=0,o=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius:t,widthSegments:e,heightSegments:n,phiStart:s,phiLength:r,thetaStart:a,thetaLength:o},e=Math.max(3,Math.floor(e)),n=Math.max(2,Math.floor(n));const c=Math.min(a+o,Math.PI);let l=0;const h=[],u=new D,d=new D,f=[],g=[],_=[],m=[];for(let p=0;p<=n;p++){const P=[],w=p/n;let y=0;p===0&&a===0?y=.5/e:p===n&&c===Math.PI&&(y=-.5/e);for(let N=0;N<=e;N++){const C=N/e;u.x=-t*Math.cos(s+C*r)*Math.sin(a+w*o),u.y=t*Math.cos(a+w*o),u.z=t*Math.sin(s+C*r)*Math.sin(a+w*o),g.push(u.x,u.y,u.z),d.copy(u).normalize(),_.push(d.x,d.y,d.z),m.push(C+y,1-w),P.push(l++)}h.push(P)}for(let p=0;p<n;p++)for(let P=0;P<e;P++){const w=h[p][P+1],y=h[p][P],N=h[p+1][P],C=h[p+1][P+1];(p!==0||a>0)&&f.push(w,y,C),(p!==n-1||c<Math.PI)&&f.push(y,N,C)}this.setIndex(f),this.setAttribute("position",new ie(g,3)),this.setAttribute("normal",new ie(_,3)),this.setAttribute("uv",new ie(m,2))}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}static fromJSON(t){return new pi(t.radius,t.widthSegments,t.heightSegments,t.phiStart,t.phiLength,t.thetaStart,t.thetaLength)}}class el extends Le{constructor(t=new Fu(new D(-1,-1,0),new D(-1,1,0),new D(1,1,0)),e=64,n=1,s=8,r=!1){super(),this.type="TubeGeometry",this.parameters={path:t,tubularSegments:e,radius:n,radialSegments:s,closed:r};const a=t.computeFrenetFrames(e,r);this.tangents=a.tangents,this.normals=a.normals,this.binormals=a.binormals;const o=new D,c=new D,l=new At;let h=new D;const u=[],d=[],f=[],g=[];_(),this.setIndex(g),this.setAttribute("position",new ie(u,3)),this.setAttribute("normal",new ie(d,3)),this.setAttribute("uv",new ie(f,2));function _(){for(let w=0;w<e;w++)m(w);m(r===!1?e:0),P(),p()}function m(w){h=t.getPointAt(w/e,h);const y=a.normals[w],N=a.binormals[w];for(let C=0;C<=s;C++){const L=C/s*Math.PI*2,I=Math.sin(L),M=-Math.cos(L);c.x=M*y.x+I*N.x,c.y=M*y.y+I*N.y,c.z=M*y.z+I*N.z,c.normalize(),d.push(c.x,c.y,c.z),o.x=h.x+n*c.x,o.y=h.y+n*c.y,o.z=h.z+n*c.z,u.push(o.x,o.y,o.z)}}function p(){for(let w=1;w<=e;w++)for(let y=1;y<=s;y++){const N=(s+1)*(w-1)+(y-1),C=(s+1)*w+(y-1),L=(s+1)*w+y,I=(s+1)*(w-1)+y;g.push(N,C,I),g.push(C,L,I)}}function P(){for(let w=0;w<=e;w++)for(let y=0;y<=s;y++)l.x=w/e,l.y=y/s,f.push(l.x,l.y)}}copy(t){return super.copy(t),this.parameters=Object.assign({},t.parameters),this}toJSON(){const t=super.toJSON();return t.path=this.parameters.path.toJSON(),t}static fromJSON(t){return new el(new Uc[t.path.type]().fromJSON(t.path),t.tubularSegments,t.radius,t.radialSegments,t.closed)}}class rv extends Hn{static get type(){return"MeshStandardMaterial"}constructor(t){super(),this.isMeshStandardMaterial=!0,this.defines={STANDARD:""},this.color=new Jt(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Jt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=za,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new pn,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.defines={STANDARD:""},this.color.copy(t.color),this.roughness=t.roughness,this.metalness=t.metalness,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.roughnessMap=t.roughnessMap,this.metalnessMap=t.metalnessMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.envMapIntensity=t.envMapIntensity,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}class Ts extends Hn{static get type(){return"MeshPhongMaterial"}constructor(t){super(),this.isMeshPhongMaterial=!0,this.color=new Jt(16777215),this.specular=new Jt(1118481),this.shininess=30,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Jt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=za,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new pn,this.combine=ka,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.specular.copy(t.specular),this.shininess=t.shininess,this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}class av extends Hn{static get type(){return"MeshLambertMaterial"}constructor(t){super(),this.isMeshLambertMaterial=!0,this.color=new Jt(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Jt(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=za,this.normalScale=new At(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new pn,this.combine=ka,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(t)}copy(t){return super.copy(t),this.color.copy(t.color),this.map=t.map,this.lightMap=t.lightMap,this.lightMapIntensity=t.lightMapIntensity,this.aoMap=t.aoMap,this.aoMapIntensity=t.aoMapIntensity,this.emissive.copy(t.emissive),this.emissiveMap=t.emissiveMap,this.emissiveIntensity=t.emissiveIntensity,this.bumpMap=t.bumpMap,this.bumpScale=t.bumpScale,this.normalMap=t.normalMap,this.normalMapType=t.normalMapType,this.normalScale.copy(t.normalScale),this.displacementMap=t.displacementMap,this.displacementScale=t.displacementScale,this.displacementBias=t.displacementBias,this.specularMap=t.specularMap,this.alphaMap=t.alphaMap,this.envMap=t.envMap,this.envMapRotation.copy(t.envMapRotation),this.combine=t.combine,this.reflectivity=t.reflectivity,this.refractionRatio=t.refractionRatio,this.wireframe=t.wireframe,this.wireframeLinewidth=t.wireframeLinewidth,this.wireframeLinecap=t.wireframeLinecap,this.wireframeLinejoin=t.wireframeLinejoin,this.flatShading=t.flatShading,this.fog=t.fog,this}}function aa(i,t,e){return!i||!e&&i.constructor===t?i:typeof t.BYTES_PER_ELEMENT=="number"?new t(i):Array.prototype.slice.call(i)}function ov(i){return ArrayBuffer.isView(i)&&!(i instanceof DataView)}function cv(i){function t(s,r){return i[s]-i[r]}const e=i.length,n=new Array(e);for(let s=0;s!==e;++s)n[s]=s;return n.sort(t),n}function Ph(i,t,e){const n=i.length,s=new i.constructor(n);for(let r=0,a=0;a!==n;++r){const o=e[r]*t;for(let c=0;c!==t;++c)s[a++]=i[o+c]}return s}function Ou(i,t,e,n){let s=1,r=i[0];for(;r!==void 0&&r[n]===void 0;)r=i[s++];if(r===void 0)return;let a=r[n];if(a!==void 0)if(Array.isArray(a))do a=r[n],a!==void 0&&(t.push(r.time),e.push.apply(e,a)),r=i[s++];while(r!==void 0);else if(a.toArray!==void 0)do a=r[n],a!==void 0&&(t.push(r.time),a.toArray(e,e.length)),r=i[s++];while(r!==void 0);else do a=r[n],a!==void 0&&(t.push(r.time),e.push(a)),r=i[s++];while(r!==void 0)}class Wa{constructor(t,e,n,s){this.parameterPositions=t,this._cachedIndex=0,this.resultBuffer=s!==void 0?s:new e.constructor(n),this.sampleValues=e,this.valueSize=n,this.settings=null,this.DefaultSettings_={}}evaluate(t){const e=this.parameterPositions;let n=this._cachedIndex,s=e[n],r=e[n-1];n:{t:{let a;e:{i:if(!(t<s)){for(let o=n+2;;){if(s===void 0){if(t<r)break i;return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}if(n===o)break;if(r=s,s=e[++n],t<s)break t}a=e.length;break e}if(!(t>=r)){const o=e[1];t<o&&(n=2,r=o);for(let c=n-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(n===c)break;if(s=r,r=e[--n-1],t>=r)break t}a=n,n=0;break e}break n}for(;n<a;){const o=n+a>>>1;t<e[o]?a=o:n=o+1}if(s=e[n],r=e[n-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(s===void 0)return n=e.length,this._cachedIndex=n,this.copySampleValue_(n-1)}this._cachedIndex=n,this.intervalChanged_(n,r,s)}return this.interpolate_(n,r,t,s)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(t){const e=this.resultBuffer,n=this.sampleValues,s=this.valueSize,r=t*s;for(let a=0;a!==s;++a)e[a]=n[r+a];return e}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}}class lv extends Wa{constructor(t,e,n,s){super(t,e,n,s),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:xl,endingEnd:xl}}intervalChanged_(t,e,n){const s=this.parameterPositions;let r=t-2,a=t+1,o=s[r],c=s[a];if(o===void 0)switch(this.getSettings_().endingStart){case yl:r=t,o=2*e-n;break;case Ml:r=s.length-2,o=e+s[r]-s[r+1];break;default:r=t,o=n}if(c===void 0)switch(this.getSettings_().endingEnd){case yl:a=t,c=2*n-e;break;case Ml:a=1,c=n+s[1]-s[0];break;default:a=t-1,c=e}const l=(n-e)*.5,h=this.valueSize;this._weightPrev=l/(e-o),this._weightNext=l/(c-n),this._offsetPrev=r*h,this._offsetNext=a*h}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=t*o,l=c-o,h=this._offsetPrev,u=this._offsetNext,d=this._weightPrev,f=this._weightNext,g=(n-e)/(s-e),_=g*g,m=_*g,p=-d*m+2*d*_-d*g,P=(1+d)*m+(-1.5-2*d)*_+(-.5+d)*g+1,w=(-1-f)*m+(1.5+f)*_+.5*g,y=f*m-f*_;for(let N=0;N!==o;++N)r[N]=p*a[h+N]+P*a[l+N]+w*a[c+N]+y*a[u+N];return r}}class hv extends Wa{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=t*o,l=c-o,h=(n-e)/(s-e),u=1-h;for(let d=0;d!==o;++d)r[d]=a[l+d]*u+a[c+d]*h;return r}}class uv extends Wa{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t){return this.copySampleValue_(t-1)}}class Jn{constructor(t,e,n,s){if(t===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(e===void 0||e.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+t);this.name=t,this.times=aa(e,this.TimeBufferType),this.values=aa(n,this.ValueBufferType),this.setInterpolation(s||this.DefaultInterpolation)}static toJSON(t){const e=t.constructor;let n;if(e.toJSON!==this.toJSON)n=e.toJSON(t);else{n={name:t.name,times:aa(t.times,Array),values:aa(t.values,Array)};const s=t.getInterpolation();s!==t.DefaultInterpolation&&(n.interpolation=s)}return n.type=t.ValueTypeName,n}InterpolantFactoryMethodDiscrete(t){return new uv(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodLinear(t){return new hv(this.times,this.values,this.getValueSize(),t)}InterpolantFactoryMethodSmooth(t){return new lv(this.times,this.values,this.getValueSize(),t)}setInterpolation(t){let e;switch(t){case ba:e=this.InterpolantFactoryMethodDiscrete;break;case Nc:e=this.InterpolantFactoryMethodLinear;break;case io:e=this.InterpolantFactoryMethodSmooth;break}if(e===void 0){const n="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(t!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(n);return console.warn("THREE.KeyframeTrack:",n),this}return this.createInterpolant=e,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return ba;case this.InterpolantFactoryMethodLinear:return Nc;case this.InterpolantFactoryMethodSmooth:return io}}getValueSize(){return this.values.length/this.times.length}shift(t){if(t!==0){const e=this.times;for(let n=0,s=e.length;n!==s;++n)e[n]+=t}return this}scale(t){if(t!==1){const e=this.times;for(let n=0,s=e.length;n!==s;++n)e[n]*=t}return this}trim(t,e){const n=this.times,s=n.length;let r=0,a=s-1;for(;r!==s&&n[r]<t;)++r;for(;a!==-1&&n[a]>e;)--a;if(++a,r!==0||a!==s){r>=a&&(a=Math.max(a,1),r=a-1);const o=this.getValueSize();this.times=n.slice(r,a),this.values=this.values.slice(r*o,a*o)}return this}validate(){let t=!0;const e=this.getValueSize();e-Math.floor(e)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),t=!1);const n=this.times,s=this.values,r=n.length;r===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),t=!1);let a=null;for(let o=0;o!==r;o++){const c=n[o];if(typeof c=="number"&&isNaN(c)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,o,c),t=!1;break}if(a!==null&&a>c){console.error("THREE.KeyframeTrack: Out of order keys.",this,o,c,a),t=!1;break}a=c}if(s!==void 0&&ov(s))for(let o=0,c=s.length;o!==c;++o){const l=s[o];if(isNaN(l)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,o,l),t=!1;break}}return t}optimize(){const t=this.times.slice(),e=this.values.slice(),n=this.getValueSize(),s=this.getInterpolation()===io,r=t.length-1;let a=1;for(let o=1;o<r;++o){let c=!1;const l=t[o],h=t[o+1];if(l!==h&&(o!==1||l!==t[0]))if(s)c=!0;else{const u=o*n,d=u-n,f=u+n;for(let g=0;g!==n;++g){const _=e[u+g];if(_!==e[d+g]||_!==e[f+g]){c=!0;break}}}if(c){if(o!==a){t[a]=t[o];const u=o*n,d=a*n;for(let f=0;f!==n;++f)e[d+f]=e[u+f]}++a}}if(r>0){t[a]=t[r];for(let o=r*n,c=a*n,l=0;l!==n;++l)e[c+l]=e[o+l];++a}return a!==t.length?(this.times=t.slice(0,a),this.values=e.slice(0,a*n)):(this.times=t,this.values=e),this}clone(){const t=this.times.slice(),e=this.values.slice(),n=this.constructor,s=new n(this.name,t,e);return s.createInterpolant=this.createInterpolant,s}}Jn.prototype.TimeBufferType=Float32Array;Jn.prototype.ValueBufferType=Float32Array;Jn.prototype.DefaultInterpolation=Nc;class Ys extends Jn{constructor(t,e,n){super(t,e,n)}}Ys.prototype.ValueTypeName="bool";Ys.prototype.ValueBufferType=Array;Ys.prototype.DefaultInterpolation=ba;Ys.prototype.InterpolantFactoryMethodLinear=void 0;Ys.prototype.InterpolantFactoryMethodSmooth=void 0;class ku extends Jn{}ku.prototype.ValueTypeName="color";class Ra extends Jn{}Ra.prototype.ValueTypeName="number";class dv extends Wa{constructor(t,e,n,s){super(t,e,n,s)}interpolate_(t,e,n,s){const r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=(n-e)/(s-e);let l=t*o;for(let h=l+o;l!==h;l+=4)Vn.slerpFlat(r,0,a,l-o,a,l,c);return r}}class Sr extends Jn{InterpolantFactoryMethodLinear(t){return new dv(this.times,this.values,this.getValueSize(),t)}}Sr.prototype.ValueTypeName="quaternion";Sr.prototype.InterpolantFactoryMethodSmooth=void 0;class $s extends Jn{constructor(t,e,n){super(t,e,n)}}$s.prototype.ValueTypeName="string";$s.prototype.ValueBufferType=Array;$s.prototype.DefaultInterpolation=ba;$s.prototype.InterpolantFactoryMethodLinear=void 0;$s.prototype.InterpolantFactoryMethodSmooth=void 0;class Fs extends Jn{}Fs.prototype.ValueTypeName="vector";class Lh{constructor(t="",e=-1,n=[],s=tf){this.name=t,this.tracks=n,this.duration=e,this.blendMode=s,this.uuid=Fi(),this.duration<0&&this.resetDuration()}static parse(t){const e=[],n=t.tracks,s=1/(t.fps||1);for(let a=0,o=n.length;a!==o;++a)e.push(pv(n[a]).scale(s));const r=new this(t.name,t.duration,e,t.blendMode);return r.uuid=t.uuid,r}static toJSON(t){const e=[],n=t.tracks,s={name:t.name,duration:t.duration,tracks:e,uuid:t.uuid,blendMode:t.blendMode};for(let r=0,a=n.length;r!==a;++r)e.push(Jn.toJSON(n[r]));return s}static CreateFromMorphTargetSequence(t,e,n,s){const r=e.length,a=[];for(let o=0;o<r;o++){let c=[],l=[];c.push((o+r-1)%r,o,(o+1)%r),l.push(0,1,0);const h=cv(c);c=Ph(c,1,h),l=Ph(l,1,h),!s&&c[0]===0&&(c.push(r),l.push(l[0])),a.push(new Ra(".morphTargetInfluences["+e[o].name+"]",c,l).scale(1/n))}return new this(t,-1,a)}static findByName(t,e){let n=t;if(!Array.isArray(t)){const s=t;n=s.geometry&&s.geometry.animations||s.animations}for(let s=0;s<n.length;s++)if(n[s].name===e)return n[s];return null}static CreateClipsFromMorphTargetSequences(t,e,n){const s={},r=/^([\w-]*?)([\d]+)$/;for(let o=0,c=t.length;o<c;o++){const l=t[o],h=l.name.match(r);if(h&&h.length>1){const u=h[1];let d=s[u];d||(s[u]=d=[]),d.push(l)}}const a=[];for(const o in s)a.push(this.CreateFromMorphTargetSequence(o,s[o],e,n));return a}static parseAnimation(t,e){if(!t)return console.error("THREE.AnimationClip: No animation in JSONLoader data."),null;const n=function(u,d,f,g,_){if(f.length!==0){const m=[],p=[];Ou(f,m,p,g),m.length!==0&&_.push(new u(d,m,p))}},s=[],r=t.name||"default",a=t.fps||30,o=t.blendMode;let c=t.length||-1;const l=t.hierarchy||[];for(let u=0;u<l.length;u++){const d=l[u].keys;if(!(!d||d.length===0))if(d[0].morphTargets){const f={};let g;for(g=0;g<d.length;g++)if(d[g].morphTargets)for(let _=0;_<d[g].morphTargets.length;_++)f[d[g].morphTargets[_]]=-1;for(const _ in f){const m=[],p=[];for(let P=0;P!==d[g].morphTargets.length;++P){const w=d[g];m.push(w.time),p.push(w.morphTarget===_?1:0)}s.push(new Ra(".morphTargetInfluence["+_+"]",m,p))}c=f.length*a}else{const f=".bones["+e[u].name+"]";n(Fs,f+".position",d,"pos",s),n(Sr,f+".quaternion",d,"rot",s),n(Fs,f+".scale",d,"scl",s)}}return s.length===0?null:new this(r,c,s,o)}resetDuration(){const t=this.tracks;let e=0;for(let n=0,s=t.length;n!==s;++n){const r=this.tracks[n];e=Math.max(e,r.times[r.times.length-1])}return this.duration=e,this}trim(){for(let t=0;t<this.tracks.length;t++)this.tracks[t].trim(0,this.duration);return this}validate(){let t=!0;for(let e=0;e<this.tracks.length;e++)t=t&&this.tracks[e].validate();return t}optimize(){for(let t=0;t<this.tracks.length;t++)this.tracks[t].optimize();return this}clone(){const t=[];for(let e=0;e<this.tracks.length;e++)t.push(this.tracks[e].clone());return new this.constructor(this.name,this.duration,t,this.blendMode)}toJSON(){return this.constructor.toJSON(this)}}function fv(i){switch(i.toLowerCase()){case"scalar":case"double":case"float":case"number":case"integer":return Ra;case"vector":case"vector2":case"vector3":case"vector4":return Fs;case"color":return ku;case"quaternion":return Sr;case"bool":case"boolean":return Ys;case"string":return $s}throw new Error("THREE.KeyframeTrack: Unsupported typeName: "+i)}function pv(i){if(i.type===void 0)throw new Error("THREE.KeyframeTrack: track type undefined, can not parse");const t=fv(i.type);if(i.times===void 0){const e=[],n=[];Ou(i.keys,e,n,"value"),i.times=e,i.values=n}return t.parse!==void 0?t.parse(i):new t(i.name,i.times,i.values,i.interpolation)}const Pa={enabled:!1,files:{},add:function(i,t){this.enabled!==!1&&(this.files[i]=t)},get:function(i){if(this.enabled!==!1)return this.files[i]},remove:function(i){delete this.files[i]},clear:function(){this.files={}}};class Bu{constructor(t,e,n){const s=this;let r=!1,a=0,o=0,c;const l=[];this.onStart=void 0,this.onLoad=t,this.onProgress=e,this.onError=n,this.itemStart=function(h){o++,r===!1&&s.onStart!==void 0&&s.onStart(h,a,o),r=!0},this.itemEnd=function(h){a++,s.onProgress!==void 0&&s.onProgress(h,a,o),a===o&&(r=!1,s.onLoad!==void 0&&s.onLoad())},this.itemError=function(h){s.onError!==void 0&&s.onError(h)},this.resolveURL=function(h){return c?c(h):h},this.setURLModifier=function(h){return c=h,this},this.addHandler=function(h,u){return l.push(h,u),this},this.removeHandler=function(h){const u=l.indexOf(h);return u!==-1&&l.splice(u,2),this},this.getHandler=function(h){for(let u=0,d=l.length;u<d;u+=2){const f=l[u],g=l[u+1];if(f.global&&(f.lastIndex=0),f.test(h))return g}return null}}}const zu=new Bu;class mi{constructor(t){this.manager=t!==void 0?t:zu,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(t,e){const n=this;return new Promise(function(s,r){n.load(t,s,e,r)})}parse(){}setCrossOrigin(t){return this.crossOrigin=t,this}setWithCredentials(t){return this.withCredentials=t,this}setPath(t){return this.path=t,this}setResourcePath(t){return this.resourcePath=t,this}setRequestHeader(t){return this.requestHeader=t,this}}mi.DEFAULT_MATERIAL_NAME="__DEFAULT";const ri={};class mv extends Error{constructor(t,e){super(t),this.response=e}}class Xa extends mi{constructor(t){super(t)}load(t,e,n,s){t===void 0&&(t=""),this.path!==void 0&&(t=this.path+t),t=this.manager.resolveURL(t);const r=Pa.get(t);if(r!==void 0)return this.manager.itemStart(t),setTimeout(()=>{e&&e(r),this.manager.itemEnd(t)},0),r;if(ri[t]!==void 0){ri[t].push({onLoad:e,onProgress:n,onError:s});return}ri[t]=[],ri[t].push({onLoad:e,onProgress:n,onError:s});const a=new Request(t,{headers:new Headers(this.requestHeader),credentials:this.withCredentials?"include":"same-origin"}),o=this.mimeType,c=this.responseType;fetch(a).then(l=>{if(l.status===200||l.status===0){if(l.status===0&&console.warn("THREE.FileLoader: HTTP Status 0 received."),typeof ReadableStream>"u"||l.body===void 0||l.body.getReader===void 0)return l;const h=ri[t],u=l.body.getReader(),d=l.headers.get("X-File-Size")||l.headers.get("Content-Length"),f=d?parseInt(d):0,g=f!==0;let _=0;const m=new ReadableStream({start(p){P();function P(){u.read().then(({done:w,value:y})=>{if(w)p.close();else{_+=y.byteLength;const N=new ProgressEvent("progress",{lengthComputable:g,loaded:_,total:f});for(let C=0,L=h.length;C<L;C++){const I=h[C];I.onProgress&&I.onProgress(N)}p.enqueue(y),P()}},w=>{p.error(w)})}}});return new Response(m)}else throw new mv(`fetch for "${l.url}" responded with ${l.status}: ${l.statusText}`,l)}).then(l=>{switch(c){case"arraybuffer":return l.arrayBuffer();case"blob":return l.blob();case"document":return l.text().then(h=>new DOMParser().parseFromString(h,o));case"json":return l.json();default:if(o===void 0)return l.text();{const u=/charset="?([^;"\s]*)"?/i.exec(o),d=u&&u[1]?u[1].toLowerCase():void 0,f=new TextDecoder(d);return l.arrayBuffer().then(g=>f.decode(g))}}}).then(l=>{Pa.add(t,l);const h=ri[t];delete ri[t];for(let u=0,d=h.length;u<d;u++){const f=h[u];f.onLoad&&f.onLoad(l)}}).catch(l=>{const h=ri[t];if(h===void 0)throw this.manager.itemError(t),l;delete ri[t];for(let u=0,d=h.length;u<d;u++){const f=h[u];f.onError&&f.onError(l)}this.manager.itemError(t)}).finally(()=>{this.manager.itemEnd(t)}),this.manager.itemStart(t)}setResponseType(t){return this.responseType=t,this}setMimeType(t){return this.mimeType=t,this}}class gv extends mi{constructor(t){super(t)}load(t,e,n,s){this.path!==void 0&&(t=this.path+t),t=this.manager.resolveURL(t);const r=this,a=Pa.get(t);if(a!==void 0)return r.manager.itemStart(t),setTimeout(function(){e&&e(a),r.manager.itemEnd(t)},0),a;const o=mr("img");function c(){h(),Pa.add(t,this),e&&e(this),r.manager.itemEnd(t)}function l(u){h(),s&&s(u),r.manager.itemError(t),r.manager.itemEnd(t)}function h(){o.removeEventListener("load",c,!1),o.removeEventListener("error",l,!1)}return o.addEventListener("load",c,!1),o.addEventListener("error",l,!1),t.slice(0,5)!=="data:"&&this.crossOrigin!==void 0&&(o.crossOrigin=this.crossOrigin),r.manager.itemStart(t),o.src=t,o}}class _v extends mi{constructor(t){super(t)}load(t,e,n,s){const r=this,a=new Du,o=new Xa(this.manager);return o.setResponseType("arraybuffer"),o.setRequestHeader(this.requestHeader),o.setPath(this.path),o.setWithCredentials(r.withCredentials),o.load(t,function(c){let l;try{l=r.parse(c)}catch(h){if(s!==void 0)s(h);else{console.error(h);return}}l.image!==void 0?a.image=l.image:l.data!==void 0&&(a.image.width=l.width,a.image.height=l.height,a.image.data=l.data),a.wrapS=l.wrapS!==void 0?l.wrapS:Bn,a.wrapT=l.wrapT!==void 0?l.wrapT:Bn,a.magFilter=l.magFilter!==void 0?l.magFilter:xn,a.minFilter=l.minFilter!==void 0?l.minFilter:xn,a.anisotropy=l.anisotropy!==void 0?l.anisotropy:1,l.colorSpace!==void 0&&(a.colorSpace=l.colorSpace),l.flipY!==void 0&&(a.flipY=l.flipY),l.format!==void 0&&(a.format=l.format),l.type!==void 0&&(a.type=l.type),l.mipmaps!==void 0&&(a.mipmaps=l.mipmaps,a.minFilter=li),l.mipmapCount===1&&(a.minFilter=xn),l.generateMipmaps!==void 0&&(a.generateMipmaps=l.generateMipmaps),a.needsUpdate=!0,e&&e(a,l)},n,s),a}}class Vu extends mi{constructor(t){super(t)}load(t,e,n,s){const r=new Je,a=new gv(this.manager);return a.setCrossOrigin(this.crossOrigin),a.setPath(this.path),a.load(t,function(o){r.image=o,r.needsUpdate=!0,e!==void 0&&e(r)},n,s),r}}class Er extends De{constructor(t,e=1){super(),this.isLight=!0,this.type="Light",this.color=new Jt(t),this.intensity=e}dispose(){}copy(t,e){return super.copy(t,e),this.color.copy(t.color),this.intensity=t.intensity,this}toJSON(t){const e=super.toJSON(t);return e.object.color=this.color.getHex(),e.object.intensity=this.intensity,this.groundColor!==void 0&&(e.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(e.object.distance=this.distance),this.angle!==void 0&&(e.object.angle=this.angle),this.decay!==void 0&&(e.object.decay=this.decay),this.penumbra!==void 0&&(e.object.penumbra=this.penumbra),this.shadow!==void 0&&(e.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(e.object.target=this.target.uuid),e}}class vv extends Er{constructor(t,e,n){super(t,n),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(De.DEFAULT_UP),this.updateMatrix(),this.groundColor=new Jt(e)}copy(t,e){return super.copy(t,e),this.groundColor.copy(t.groundColor),this}}const Bo=new Yt,Nh=new D,Dh=new D;class nl{constructor(t){this.camera=t,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new At(512,512),this.map=null,this.mapPass=null,this.matrix=new Yt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Yc,this._frameExtents=new At(1,1),this._viewportCount=1,this._viewports=[new ye(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(t){const e=this.camera,n=this.matrix;Nh.setFromMatrixPosition(t.matrixWorld),e.position.copy(Nh),Dh.setFromMatrixPosition(t.target.matrixWorld),e.lookAt(Dh),e.updateMatrixWorld(),Bo.multiplyMatrices(e.projectionMatrix,e.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Bo),n.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),n.multiply(Bo)}getViewport(t){return this._viewports[t]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(t){return this.camera=t.camera.clone(),this.intensity=t.intensity,this.bias=t.bias,this.radius=t.radius,this.mapSize.copy(t.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){const t={};return this.intensity!==1&&(t.intensity=this.intensity),this.bias!==0&&(t.bias=this.bias),this.normalBias!==0&&(t.normalBias=this.normalBias),this.radius!==1&&(t.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(t.mapSize=this.mapSize.toArray()),t.camera=this.camera.toJSON(!1).object,delete t.camera.matrix,t}}class xv extends nl{constructor(){super(new tn(50,1,.5,500)),this.isSpotLightShadow=!0,this.focus=1}updateMatrices(t){const e=this.camera,n=Is*2*t.angle*this.focus,s=this.mapSize.width/this.mapSize.height,r=t.distance||e.far;(n!==e.fov||s!==e.aspect||r!==e.far)&&(e.fov=n,e.aspect=s,e.far=r,e.updateProjectionMatrix()),super.updateMatrices(t)}copy(t){return super.copy(t),this.focus=t.focus,this}}class yv extends Er{constructor(t,e,n=0,s=Math.PI/3,r=0,a=2){super(t,e),this.isSpotLight=!0,this.type="SpotLight",this.position.copy(De.DEFAULT_UP),this.updateMatrix(),this.target=new De,this.distance=n,this.angle=s,this.penumbra=r,this.decay=a,this.map=null,this.shadow=new xv}get power(){return this.intensity*Math.PI}set power(t){this.intensity=t/Math.PI}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.angle=t.angle,this.penumbra=t.penumbra,this.decay=t.decay,this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}}const Ih=new Yt,sr=new D,zo=new D;class Mv extends nl{constructor(){super(new tn(90,1,.5,500)),this.isPointLightShadow=!0,this._frameExtents=new At(4,2),this._viewportCount=6,this._viewports=[new ye(2,1,1,1),new ye(0,1,1,1),new ye(3,1,1,1),new ye(1,1,1,1),new ye(3,0,1,1),new ye(1,0,1,1)],this._cubeDirections=[new D(1,0,0),new D(-1,0,0),new D(0,0,1),new D(0,0,-1),new D(0,1,0),new D(0,-1,0)],this._cubeUps=[new D(0,1,0),new D(0,1,0),new D(0,1,0),new D(0,1,0),new D(0,0,1),new D(0,0,-1)]}updateMatrices(t,e=0){const n=this.camera,s=this.matrix,r=t.distance||n.far;r!==n.far&&(n.far=r,n.updateProjectionMatrix()),sr.setFromMatrixPosition(t.matrixWorld),n.position.copy(sr),zo.copy(n.position),zo.add(this._cubeDirections[e]),n.up.copy(this._cubeUps[e]),n.lookAt(zo),n.updateMatrixWorld(),s.makeTranslation(-sr.x,-sr.y,-sr.z),Ih.multiplyMatrices(n.projectionMatrix,n.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Ih)}}class bv extends Er{constructor(t,e,n=0,s=2){super(t,e),this.isPointLight=!0,this.type="PointLight",this.distance=n,this.decay=s,this.shadow=new Mv}get power(){return this.intensity*4*Math.PI}set power(t){this.intensity=t/(4*Math.PI)}dispose(){this.shadow.dispose()}copy(t,e){return super.copy(t,e),this.distance=t.distance,this.decay=t.decay,this.shadow=t.shadow.clone(),this}}class Sv extends nl{constructor(){super(new $c(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}}class Hu extends Er{constructor(t,e){super(t,e),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(De.DEFAULT_UP),this.updateMatrix(),this.target=new De,this.shadow=new Sv}dispose(){this.shadow.dispose()}copy(t){return super.copy(t),this.target=t.target.clone(),this.shadow=t.shadow.clone(),this}}class Ev extends Er{constructor(t,e){super(t,e),this.isAmbientLight=!0,this.type="AmbientLight"}}class Gu{static decodeText(t){if(console.warn("THREE.LoaderUtils: decodeText() has been deprecated with r165 and will be removed with r175. Use TextDecoder instead."),typeof TextDecoder<"u")return new TextDecoder().decode(t);let e="";for(let n=0,s=t.length;n<s;n++)e+=String.fromCharCode(t[n]);try{return decodeURIComponent(escape(e))}catch{return e}}static extractUrlBase(t){const e=t.lastIndexOf("/");return e===-1?"./":t.slice(0,e+1)}static resolveURL(t,e){return typeof t!="string"||t===""?"":(/^https?:\/\//i.test(e)&&/^\//.test(t)&&(e=e.replace(/(^https?:\/\/[^\/]+).*/i,"$1")),/^(https?:)?\/\//i.test(t)||/^data:.*,.*$/i.test(t)||/^blob:.*$/i.test(t)?t:e+t)}}const Uh=new Yt;class wv{constructor(t,e,n=0,s=1/0){this.ray=new Gs(t,e),this.near=n,this.far=s,this.camera=null,this.layers=new jc,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(t,e){this.ray.set(t,e)}setFromCamera(t,e){e.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(e.matrixWorld),this.ray.direction.set(t.x,t.y,.5).unproject(e).sub(this.ray.origin).normalize(),this.camera=e):e.isOrthographicCamera?(this.ray.origin.set(t.x,t.y,(e.near+e.far)/(e.near-e.far)).unproject(e),this.ray.direction.set(0,0,-1).transformDirection(e.matrixWorld),this.camera=e):console.error("THREE.Raycaster: Unsupported camera type: "+e.type)}setFromXRController(t){return Uh.identity().extractRotation(t.matrixWorld),this.ray.origin.setFromMatrixPosition(t.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(Uh),this}intersectObject(t,e=!0,n=[]){return Fc(t,this,n,e),n.sort(Fh),n}intersectObjects(t,e=!0,n=[]){for(let s=0,r=t.length;s<r;s++)Fc(t[s],this,n,e);return n.sort(Fh),n}}function Fh(i,t){return i.distance-t.distance}function Fc(i,t,e,n){let s=!0;if(i.layers.test(t.layers)&&i.raycast(t,e)===!1&&(s=!1),s===!0&&n===!0){const r=i.children;for(let a=0,o=r.length;a<o;a++)Fc(r[a],t,e,!0)}}class Oh{constructor(t=1,e=0,n=0){return this.radius=t,this.phi=e,this.theta=n,this}set(t,e,n){return this.radius=t,this.phi=e,this.theta=n,this}copy(t){return this.radius=t.radius,this.phi=t.phi,this.theta=t.theta,this}makeSafe(){return this.phi=Math.max(1e-6,Math.min(Math.PI-1e-6,this.phi)),this}setFromVector3(t){return this.setFromCartesianCoords(t.x,t.y,t.z)}setFromCartesianCoords(t,e,n){return this.radius=Math.sqrt(t*t+e*e+n*n),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(t,n),this.phi=Math.acos(Ye(e/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}}class Tv extends Ta{constructor(t=10,e=10,n=4473924,s=8947848){n=new Jt(n),s=new Jt(s);const r=e/2,a=t/e,o=t/2,c=[],l=[];for(let d=0,f=0,g=-o;d<=e;d++,g+=a){c.push(-o,0,g,o,0,g),c.push(g,0,-o,g,0,o);const _=d===r?n:s;_.toArray(l,f),f+=3,_.toArray(l,f),f+=3,_.toArray(l,f),f+=3,_.toArray(l,f),f+=3}const h=new Le;h.setAttribute("position",new ie(c,3)),h.setAttribute("color",new ie(l,3));const u=new zn({vertexColors:!0,toneMapped:!1});super(h,u),this.type="GridHelper"}dispose(){this.geometry.dispose(),this.material.dispose()}}const kh=new D;let oa,Vo;class Zi extends De{constructor(t=new D(0,0,1),e=new D(0,0,0),n=1,s=16776960,r=n*.2,a=r*.2){super(),this.type="ArrowHelper",oa===void 0&&(oa=new Le,oa.setAttribute("position",new ie([0,0,0,0,1,0],3)),Vo=new js(0,.5,1,5,1),Vo.translate(0,-.5,0)),this.position.copy(e),this.line=new qs(oa,new zn({color:s,toneMapped:!1})),this.line.matrixAutoUpdate=!1,this.add(this.line),this.cone=new ge(Vo,new Ke({color:s,toneMapped:!1})),this.cone.matrixAutoUpdate=!1,this.add(this.cone),this.setDirection(t),this.setLength(n,r,a)}setDirection(t){if(t.y>.99999)this.quaternion.set(0,0,0,1);else if(t.y<-.99999)this.quaternion.set(1,0,0,0);else{kh.set(t.z,0,-t.x).normalize();const e=Math.acos(t.y);this.quaternion.setFromAxisAngle(kh,e)}}setLength(t,e=t*.2,n=e*.2){this.line.scale.set(1,Math.max(1e-4,t-e),1),this.line.updateMatrix(),this.cone.scale.set(n,e,n),this.cone.position.y=t,this.cone.updateMatrix()}setColor(t){this.line.material.color.set(t),this.cone.material.color.set(t)}copy(t){return super.copy(t,!1),this.line.copy(t.line),this.cone.copy(t.cone),this}dispose(){this.line.geometry.dispose(),this.line.material.dispose(),this.cone.geometry.dispose(),this.cone.material.dispose()}}class Av extends ts{constructor(t,e=null){super(),this.object=t,this.domElement=e,this.enabled=!0,this.state=-1,this.keys={},this.mouseButtons={LEFT:null,MIDDLE:null,RIGHT:null},this.touches={ONE:null,TWO:null}}connect(){}disconnect(){}dispose(){}update(){}}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:Bc}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__=Bc);const Bh={type:"change"},il={type:"start"},Wu={type:"end"},ca=new Gs,zh=new ci,Cv=Math.cos(70*Ri.DEG2RAD),He=new D,un=2*Math.PI,Te={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},Ho=1e-6;class Rv extends Av{constructor(t,e=null){super(t,e),this.state=Te.NONE,this.enabled=!0,this.target=new D,this.cursor=new D,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:bs.ROTATE,MIDDLE:bs.DOLLY,RIGHT:bs.PAN},this.touches={ONE:ys.ROTATE,TWO:ys.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this._lastPosition=new D,this._lastQuaternion=new Vn,this._lastTargetPosition=new D,this._quat=new Vn().setFromUnitVectors(t.up,new D(0,1,0)),this._quatInverse=this._quat.clone().invert(),this._spherical=new Oh,this._sphericalDelta=new Oh,this._scale=1,this._panOffset=new D,this._rotateStart=new At,this._rotateEnd=new At,this._rotateDelta=new At,this._panStart=new At,this._panEnd=new At,this._panDelta=new At,this._dollyStart=new At,this._dollyEnd=new At,this._dollyDelta=new At,this._dollyDirection=new D,this._mouse=new At,this._performCursorZoom=!1,this._pointers=[],this._pointerPositions={},this._controlActive=!1,this._onPointerMove=Lv.bind(this),this._onPointerDown=Pv.bind(this),this._onPointerUp=Nv.bind(this),this._onContextMenu=Bv.bind(this),this._onMouseWheel=Uv.bind(this),this._onKeyDown=Fv.bind(this),this._onTouchStart=Ov.bind(this),this._onTouchMove=kv.bind(this),this._onMouseDown=Dv.bind(this),this._onMouseMove=Iv.bind(this),this._interceptControlDown=zv.bind(this),this._interceptControlUp=Vv.bind(this),this.domElement!==null&&this.connect(),this.update()}connect(){this.domElement.addEventListener("pointerdown",this._onPointerDown),this.domElement.addEventListener("pointercancel",this._onPointerUp),this.domElement.addEventListener("contextmenu",this._onContextMenu),this.domElement.addEventListener("wheel",this._onMouseWheel,{passive:!1}),this.domElement.getRootNode().addEventListener("keydown",this._interceptControlDown,{passive:!0,capture:!0}),this.domElement.style.touchAction="none"}disconnect(){this.domElement.removeEventListener("pointerdown",this._onPointerDown),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.domElement.removeEventListener("pointercancel",this._onPointerUp),this.domElement.removeEventListener("wheel",this._onMouseWheel),this.domElement.removeEventListener("contextmenu",this._onContextMenu),this.stopListenToKeyEvents(),this.domElement.getRootNode().removeEventListener("keydown",this._interceptControlDown,{capture:!0}),this.domElement.style.touchAction="auto"}dispose(){this.disconnect()}getPolarAngle(){return this._spherical.phi}getAzimuthalAngle(){return this._spherical.theta}getDistance(){return this.object.position.distanceTo(this.target)}listenToKeyEvents(t){t.addEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=t}stopListenToKeyEvents(){this._domElementKeyEvents!==null&&(this._domElementKeyEvents.removeEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=null)}saveState(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom}reset(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent(Bh),this.update(),this.state=Te.NONE}update(t=null){const e=this.object.position;He.copy(e).sub(this.target),He.applyQuaternion(this._quat),this._spherical.setFromVector3(He),this.autoRotate&&this.state===Te.NONE&&this._rotateLeft(this._getAutoRotationAngle(t)),this.enableDamping?(this._spherical.theta+=this._sphericalDelta.theta*this.dampingFactor,this._spherical.phi+=this._sphericalDelta.phi*this.dampingFactor):(this._spherical.theta+=this._sphericalDelta.theta,this._spherical.phi+=this._sphericalDelta.phi);let n=this.minAzimuthAngle,s=this.maxAzimuthAngle;isFinite(n)&&isFinite(s)&&(n<-Math.PI?n+=un:n>Math.PI&&(n-=un),s<-Math.PI?s+=un:s>Math.PI&&(s-=un),n<=s?this._spherical.theta=Math.max(n,Math.min(s,this._spherical.theta)):this._spherical.theta=this._spherical.theta>(n+s)/2?Math.max(n,this._spherical.theta):Math.min(s,this._spherical.theta)),this._spherical.phi=Math.max(this.minPolarAngle,Math.min(this.maxPolarAngle,this._spherical.phi)),this._spherical.makeSafe(),this.enableDamping===!0?this.target.addScaledVector(this._panOffset,this.dampingFactor):this.target.add(this._panOffset),this.target.sub(this.cursor),this.target.clampLength(this.minTargetRadius,this.maxTargetRadius),this.target.add(this.cursor);let r=!1;if(this.zoomToCursor&&this._performCursorZoom||this.object.isOrthographicCamera)this._spherical.radius=this._clampDistance(this._spherical.radius);else{const a=this._spherical.radius;this._spherical.radius=this._clampDistance(this._spherical.radius*this._scale),r=a!=this._spherical.radius}if(He.setFromSpherical(this._spherical),He.applyQuaternion(this._quatInverse),e.copy(this.target).add(He),this.object.lookAt(this.target),this.enableDamping===!0?(this._sphericalDelta.theta*=1-this.dampingFactor,this._sphericalDelta.phi*=1-this.dampingFactor,this._panOffset.multiplyScalar(1-this.dampingFactor)):(this._sphericalDelta.set(0,0,0),this._panOffset.set(0,0,0)),this.zoomToCursor&&this._performCursorZoom){let a=null;if(this.object.isPerspectiveCamera){const o=He.length();a=this._clampDistance(o*this._scale);const c=o-a;this.object.position.addScaledVector(this._dollyDirection,c),this.object.updateMatrixWorld(),r=!!c}else if(this.object.isOrthographicCamera){const o=new D(this._mouse.x,this._mouse.y,0);o.unproject(this.object);const c=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),this.object.updateProjectionMatrix(),r=c!==this.object.zoom;const l=new D(this._mouse.x,this._mouse.y,0);l.unproject(this.object),this.object.position.sub(l).add(o),this.object.updateMatrixWorld(),a=He.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),this.zoomToCursor=!1;a!==null&&(this.screenSpacePanning?this.target.set(0,0,-1).transformDirection(this.object.matrix).multiplyScalar(a).add(this.object.position):(ca.origin.copy(this.object.position),ca.direction.set(0,0,-1).transformDirection(this.object.matrix),Math.abs(this.object.up.dot(ca.direction))<Cv?this.object.lookAt(this.target):(zh.setFromNormalAndCoplanarPoint(this.object.up,this.target),ca.intersectPlane(zh,this.target))))}else if(this.object.isOrthographicCamera){const a=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),a!==this.object.zoom&&(this.object.updateProjectionMatrix(),r=!0)}return this._scale=1,this._performCursorZoom=!1,r||this._lastPosition.distanceToSquared(this.object.position)>Ho||8*(1-this._lastQuaternion.dot(this.object.quaternion))>Ho||this._lastTargetPosition.distanceToSquared(this.target)>Ho?(this.dispatchEvent(Bh),this._lastPosition.copy(this.object.position),this._lastQuaternion.copy(this.object.quaternion),this._lastTargetPosition.copy(this.target),!0):!1}_getAutoRotationAngle(t){return t!==null?un/60*this.autoRotateSpeed*t:un/60/60*this.autoRotateSpeed}_getZoomScale(t){const e=Math.abs(t*.01);return Math.pow(.95,this.zoomSpeed*e)}_rotateLeft(t){this._sphericalDelta.theta-=t}_rotateUp(t){this._sphericalDelta.phi-=t}_panLeft(t,e){He.setFromMatrixColumn(e,0),He.multiplyScalar(-t),this._panOffset.add(He)}_panUp(t,e){this.screenSpacePanning===!0?He.setFromMatrixColumn(e,1):(He.setFromMatrixColumn(e,0),He.crossVectors(this.object.up,He)),He.multiplyScalar(t),this._panOffset.add(He)}_pan(t,e){const n=this.domElement;if(this.object.isPerspectiveCamera){const s=this.object.position;He.copy(s).sub(this.target);let r=He.length();r*=Math.tan(this.object.fov/2*Math.PI/180),this._panLeft(2*t*r/n.clientHeight,this.object.matrix),this._panUp(2*e*r/n.clientHeight,this.object.matrix)}else this.object.isOrthographicCamera?(this._panLeft(t*(this.object.right-this.object.left)/this.object.zoom/n.clientWidth,this.object.matrix),this._panUp(e*(this.object.top-this.object.bottom)/this.object.zoom/n.clientHeight,this.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),this.enablePan=!1)}_dollyOut(t){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale/=t:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_dollyIn(t){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale*=t:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_updateZoomParameters(t,e){if(!this.zoomToCursor)return;this._performCursorZoom=!0;const n=this.domElement.getBoundingClientRect(),s=t-n.left,r=e-n.top,a=n.width,o=n.height;this._mouse.x=s/a*2-1,this._mouse.y=-(r/o)*2+1,this._dollyDirection.set(this._mouse.x,this._mouse.y,1).unproject(this.object).sub(this.object.position).normalize()}_clampDistance(t){return Math.max(this.minDistance,Math.min(this.maxDistance,t))}_handleMouseDownRotate(t){this._rotateStart.set(t.clientX,t.clientY)}_handleMouseDownDolly(t){this._updateZoomParameters(t.clientX,t.clientX),this._dollyStart.set(t.clientX,t.clientY)}_handleMouseDownPan(t){this._panStart.set(t.clientX,t.clientY)}_handleMouseMoveRotate(t){this._rotateEnd.set(t.clientX,t.clientY),this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const e=this.domElement;this._rotateLeft(un*this._rotateDelta.x/e.clientHeight),this._rotateUp(un*this._rotateDelta.y/e.clientHeight),this._rotateStart.copy(this._rotateEnd),this.update()}_handleMouseMoveDolly(t){this._dollyEnd.set(t.clientX,t.clientY),this._dollyDelta.subVectors(this._dollyEnd,this._dollyStart),this._dollyDelta.y>0?this._dollyOut(this._getZoomScale(this._dollyDelta.y)):this._dollyDelta.y<0&&this._dollyIn(this._getZoomScale(this._dollyDelta.y)),this._dollyStart.copy(this._dollyEnd),this.update()}_handleMouseMovePan(t){this._panEnd.set(t.clientX,t.clientY),this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd),this.update()}_handleMouseWheel(t){this._updateZoomParameters(t.clientX,t.clientY),t.deltaY<0?this._dollyIn(this._getZoomScale(t.deltaY)):t.deltaY>0&&this._dollyOut(this._getZoomScale(t.deltaY)),this.update()}_handleKeyDown(t){let e=!1;switch(t.code){case this.keys.UP:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateUp(un*this.rotateSpeed/this.domElement.clientHeight):this._pan(0,this.keyPanSpeed),e=!0;break;case this.keys.BOTTOM:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateUp(-un*this.rotateSpeed/this.domElement.clientHeight):this._pan(0,-this.keyPanSpeed),e=!0;break;case this.keys.LEFT:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateLeft(un*this.rotateSpeed/this.domElement.clientHeight):this._pan(this.keyPanSpeed,0),e=!0;break;case this.keys.RIGHT:t.ctrlKey||t.metaKey||t.shiftKey?this._rotateLeft(-un*this.rotateSpeed/this.domElement.clientHeight):this._pan(-this.keyPanSpeed,0),e=!0;break}e&&(t.preventDefault(),this.update())}_handleTouchStartRotate(t){if(this._pointers.length===1)this._rotateStart.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._rotateStart.set(n,s)}}_handleTouchStartPan(t){if(this._pointers.length===1)this._panStart.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._panStart.set(n,s)}}_handleTouchStartDolly(t){const e=this._getSecondPointerPosition(t),n=t.pageX-e.x,s=t.pageY-e.y,r=Math.sqrt(n*n+s*s);this._dollyStart.set(0,r)}_handleTouchStartDollyPan(t){this.enableZoom&&this._handleTouchStartDolly(t),this.enablePan&&this._handleTouchStartPan(t)}_handleTouchStartDollyRotate(t){this.enableZoom&&this._handleTouchStartDolly(t),this.enableRotate&&this._handleTouchStartRotate(t)}_handleTouchMoveRotate(t){if(this._pointers.length==1)this._rotateEnd.set(t.pageX,t.pageY);else{const n=this._getSecondPointerPosition(t),s=.5*(t.pageX+n.x),r=.5*(t.pageY+n.y);this._rotateEnd.set(s,r)}this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);const e=this.domElement;this._rotateLeft(un*this._rotateDelta.x/e.clientHeight),this._rotateUp(un*this._rotateDelta.y/e.clientHeight),this._rotateStart.copy(this._rotateEnd)}_handleTouchMovePan(t){if(this._pointers.length===1)this._panEnd.set(t.pageX,t.pageY);else{const e=this._getSecondPointerPosition(t),n=.5*(t.pageX+e.x),s=.5*(t.pageY+e.y);this._panEnd.set(n,s)}this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd)}_handleTouchMoveDolly(t){const e=this._getSecondPointerPosition(t),n=t.pageX-e.x,s=t.pageY-e.y,r=Math.sqrt(n*n+s*s);this._dollyEnd.set(0,r),this._dollyDelta.set(0,Math.pow(this._dollyEnd.y/this._dollyStart.y,this.zoomSpeed)),this._dollyOut(this._dollyDelta.y),this._dollyStart.copy(this._dollyEnd);const a=(t.pageX+e.x)*.5,o=(t.pageY+e.y)*.5;this._updateZoomParameters(a,o)}_handleTouchMoveDollyPan(t){this.enableZoom&&this._handleTouchMoveDolly(t),this.enablePan&&this._handleTouchMovePan(t)}_handleTouchMoveDollyRotate(t){this.enableZoom&&this._handleTouchMoveDolly(t),this.enableRotate&&this._handleTouchMoveRotate(t)}_addPointer(t){this._pointers.push(t.pointerId)}_removePointer(t){delete this._pointerPositions[t.pointerId];for(let e=0;e<this._pointers.length;e++)if(this._pointers[e]==t.pointerId){this._pointers.splice(e,1);return}}_isTrackingPointer(t){for(let e=0;e<this._pointers.length;e++)if(this._pointers[e]==t.pointerId)return!0;return!1}_trackPointer(t){let e=this._pointerPositions[t.pointerId];e===void 0&&(e=new At,this._pointerPositions[t.pointerId]=e),e.set(t.pageX,t.pageY)}_getSecondPointerPosition(t){const e=t.pointerId===this._pointers[0]?this._pointers[1]:this._pointers[0];return this._pointerPositions[e]}_customWheelEvent(t){const e=t.deltaMode,n={clientX:t.clientX,clientY:t.clientY,deltaY:t.deltaY};switch(e){case 1:n.deltaY*=16;break;case 2:n.deltaY*=100;break}return t.ctrlKey&&!this._controlActive&&(n.deltaY*=10),n}}function Pv(i){this.enabled!==!1&&(this._pointers.length===0&&(this.domElement.setPointerCapture(i.pointerId),this.domElement.addEventListener("pointermove",this._onPointerMove),this.domElement.addEventListener("pointerup",this._onPointerUp)),!this._isTrackingPointer(i)&&(this._addPointer(i),i.pointerType==="touch"?this._onTouchStart(i):this._onMouseDown(i)))}function Lv(i){this.enabled!==!1&&(i.pointerType==="touch"?this._onTouchMove(i):this._onMouseMove(i))}function Nv(i){switch(this._removePointer(i),this._pointers.length){case 0:this.domElement.releasePointerCapture(i.pointerId),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.dispatchEvent(Wu),this.state=Te.NONE;break;case 1:const t=this._pointers[0],e=this._pointerPositions[t];this._onTouchStart({pointerId:t,pageX:e.x,pageY:e.y});break}}function Dv(i){let t;switch(i.button){case 0:t=this.mouseButtons.LEFT;break;case 1:t=this.mouseButtons.MIDDLE;break;case 2:t=this.mouseButtons.RIGHT;break;default:t=-1}switch(t){case bs.DOLLY:if(this.enableZoom===!1)return;this._handleMouseDownDolly(i),this.state=Te.DOLLY;break;case bs.ROTATE:if(i.ctrlKey||i.metaKey||i.shiftKey){if(this.enablePan===!1)return;this._handleMouseDownPan(i),this.state=Te.PAN}else{if(this.enableRotate===!1)return;this._handleMouseDownRotate(i),this.state=Te.ROTATE}break;case bs.PAN:if(i.ctrlKey||i.metaKey||i.shiftKey){if(this.enableRotate===!1)return;this._handleMouseDownRotate(i),this.state=Te.ROTATE}else{if(this.enablePan===!1)return;this._handleMouseDownPan(i),this.state=Te.PAN}break;default:this.state=Te.NONE}this.state!==Te.NONE&&this.dispatchEvent(il)}function Iv(i){switch(this.state){case Te.ROTATE:if(this.enableRotate===!1)return;this._handleMouseMoveRotate(i);break;case Te.DOLLY:if(this.enableZoom===!1)return;this._handleMouseMoveDolly(i);break;case Te.PAN:if(this.enablePan===!1)return;this._handleMouseMovePan(i);break}}function Uv(i){this.enabled===!1||this.enableZoom===!1||this.state!==Te.NONE||(i.preventDefault(),this.dispatchEvent(il),this._handleMouseWheel(this._customWheelEvent(i)),this.dispatchEvent(Wu))}function Fv(i){this.enabled===!1||this.enablePan===!1||this._handleKeyDown(i)}function Ov(i){switch(this._trackPointer(i),this._pointers.length){case 1:switch(this.touches.ONE){case ys.ROTATE:if(this.enableRotate===!1)return;this._handleTouchStartRotate(i),this.state=Te.TOUCH_ROTATE;break;case ys.PAN:if(this.enablePan===!1)return;this._handleTouchStartPan(i),this.state=Te.TOUCH_PAN;break;default:this.state=Te.NONE}break;case 2:switch(this.touches.TWO){case ys.DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchStartDollyPan(i),this.state=Te.TOUCH_DOLLY_PAN;break;case ys.DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchStartDollyRotate(i),this.state=Te.TOUCH_DOLLY_ROTATE;break;default:this.state=Te.NONE}break;default:this.state=Te.NONE}this.state!==Te.NONE&&this.dispatchEvent(il)}function kv(i){switch(this._trackPointer(i),this.state){case Te.TOUCH_ROTATE:if(this.enableRotate===!1)return;this._handleTouchMoveRotate(i),this.update();break;case Te.TOUCH_PAN:if(this.enablePan===!1)return;this._handleTouchMovePan(i),this.update();break;case Te.TOUCH_DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchMoveDollyPan(i),this.update();break;case Te.TOUCH_DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchMoveDollyRotate(i),this.update();break;default:this.state=Te.NONE}}function Bv(i){this.enabled!==!1&&i.preventDefault()}function zv(i){i.key==="Control"&&(this._controlActive=!0,this.domElement.getRootNode().addEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function Vv(i){i.key==="Control"&&(this._controlActive=!1,this.domElement.getRootNode().removeEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}const Hv=/^[og]\s*(.+)?/,Gv=/^mtllib /,Wv=/^usemtl /,Xv=/^usemap /,Vh=/\s+/,Hh=new D,Go=new D,Gh=new D,Wh=new D,Rn=new D,la=new Jt;function qv(){const i={objects:[],object:{},vertices:[],normals:[],colors:[],uvs:[],materials:{},materialLibraries:[],startObject:function(t,e){if(this.object&&this.object.fromDeclaration===!1){this.object.name=t,this.object.fromDeclaration=e!==!1;return}const n=this.object&&typeof this.object.currentMaterial=="function"?this.object.currentMaterial():void 0;if(this.object&&typeof this.object._finalize=="function"&&this.object._finalize(!0),this.object={name:t||"",fromDeclaration:e!==!1,geometry:{vertices:[],normals:[],colors:[],uvs:[],hasUVIndices:!1},materials:[],smooth:!0,startMaterial:function(s,r){const a=this._finalize(!1);a&&(a.inherited||a.groupCount<=0)&&this.materials.splice(a.index,1);const o={index:this.materials.length,name:s||"",mtllib:Array.isArray(r)&&r.length>0?r[r.length-1]:"",smooth:a!==void 0?a.smooth:this.smooth,groupStart:a!==void 0?a.groupEnd:0,groupEnd:-1,groupCount:-1,inherited:!1,clone:function(c){const l={index:typeof c=="number"?c:this.index,name:this.name,mtllib:this.mtllib,smooth:this.smooth,groupStart:0,groupEnd:-1,groupCount:-1,inherited:!1};return l.clone=this.clone.bind(l),l}};return this.materials.push(o),o},currentMaterial:function(){if(this.materials.length>0)return this.materials[this.materials.length-1]},_finalize:function(s){const r=this.currentMaterial();if(r&&r.groupEnd===-1&&(r.groupEnd=this.geometry.vertices.length/3,r.groupCount=r.groupEnd-r.groupStart,r.inherited=!1),s&&this.materials.length>1)for(let a=this.materials.length-1;a>=0;a--)this.materials[a].groupCount<=0&&this.materials.splice(a,1);return s&&this.materials.length===0&&this.materials.push({name:"",smooth:this.smooth}),r}},n&&n.name&&typeof n.clone=="function"){const s=n.clone(0);s.inherited=!0,this.object.materials.push(s)}this.objects.push(this.object)},finalize:function(){this.object&&typeof this.object._finalize=="function"&&this.object._finalize(!0)},parseVertexIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/3)*3},parseNormalIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/3)*3},parseUVIndex:function(t,e){const n=parseInt(t,10);return(n>=0?n-1:n+e/2)*2},addVertex:function(t,e,n){const s=this.vertices,r=this.object.geometry.vertices;r.push(s[t+0],s[t+1],s[t+2]),r.push(s[e+0],s[e+1],s[e+2]),r.push(s[n+0],s[n+1],s[n+2])},addVertexPoint:function(t){const e=this.vertices;this.object.geometry.vertices.push(e[t+0],e[t+1],e[t+2])},addVertexLine:function(t){const e=this.vertices;this.object.geometry.vertices.push(e[t+0],e[t+1],e[t+2])},addNormal:function(t,e,n){const s=this.normals,r=this.object.geometry.normals;r.push(s[t+0],s[t+1],s[t+2]),r.push(s[e+0],s[e+1],s[e+2]),r.push(s[n+0],s[n+1],s[n+2])},addFaceNormal:function(t,e,n){const s=this.vertices,r=this.object.geometry.normals;Hh.fromArray(s,t),Go.fromArray(s,e),Gh.fromArray(s,n),Rn.subVectors(Gh,Go),Wh.subVectors(Hh,Go),Rn.cross(Wh),Rn.normalize(),r.push(Rn.x,Rn.y,Rn.z),r.push(Rn.x,Rn.y,Rn.z),r.push(Rn.x,Rn.y,Rn.z)},addColor:function(t,e,n){const s=this.colors,r=this.object.geometry.colors;s[t]!==void 0&&r.push(s[t+0],s[t+1],s[t+2]),s[e]!==void 0&&r.push(s[e+0],s[e+1],s[e+2]),s[n]!==void 0&&r.push(s[n+0],s[n+1],s[n+2])},addUV:function(t,e,n){const s=this.uvs,r=this.object.geometry.uvs;r.push(s[t+0],s[t+1]),r.push(s[e+0],s[e+1]),r.push(s[n+0],s[n+1])},addDefaultUV:function(){const t=this.object.geometry.uvs;t.push(0,0),t.push(0,0),t.push(0,0)},addUVLine:function(t){const e=this.uvs;this.object.geometry.uvs.push(e[t+0],e[t+1])},addFace:function(t,e,n,s,r,a,o,c,l){const h=this.vertices.length;let u=this.parseVertexIndex(t,h),d=this.parseVertexIndex(e,h),f=this.parseVertexIndex(n,h);if(this.addVertex(u,d,f),this.addColor(u,d,f),o!==void 0&&o!==""){const g=this.normals.length;u=this.parseNormalIndex(o,g),d=this.parseNormalIndex(c,g),f=this.parseNormalIndex(l,g),this.addNormal(u,d,f)}else this.addFaceNormal(u,d,f);if(s!==void 0&&s!==""){const g=this.uvs.length;u=this.parseUVIndex(s,g),d=this.parseUVIndex(r,g),f=this.parseUVIndex(a,g),this.addUV(u,d,f),this.object.geometry.hasUVIndices=!0}else this.addDefaultUV()},addPointGeometry:function(t){this.object.geometry.type="Points";const e=this.vertices.length;for(let n=0,s=t.length;n<s;n++){const r=this.parseVertexIndex(t[n],e);this.addVertexPoint(r),this.addColor(r)}},addLineGeometry:function(t,e){this.object.geometry.type="Line";const n=this.vertices.length,s=this.uvs.length;for(let r=0,a=t.length;r<a;r++)this.addVertexLine(this.parseVertexIndex(t[r],n));for(let r=0,a=e.length;r<a;r++)this.addUVLine(this.parseUVIndex(e[r],s))}};return i.startObject("",!1),i}class Wo extends mi{constructor(t){super(t),this.materials=null}load(t,e,n,s){const r=this,a=new Xa(this.manager);a.setPath(this.path),a.setRequestHeader(this.requestHeader),a.setWithCredentials(this.withCredentials),a.load(t,function(o){try{e(r.parse(o))}catch(c){s?s(c):console.error(c),r.manager.itemError(t)}},n,s)}setMaterials(t){return this.materials=t,this}parse(t){const e=new qv;t.indexOf(`\r
`)!==-1&&(t=t.replace(/\r\n/g,`
`)),t.indexOf(`\\
`)!==-1&&(t=t.replace(/\\\n/g,""));const n=t.split(`
`);let s=[];for(let o=0,c=n.length;o<c;o++){const l=n[o].trimStart();if(l.length===0)continue;const h=l.charAt(0);if(h!=="#")if(h==="v"){const u=l.split(Vh);switch(u[0]){case"v":e.vertices.push(parseFloat(u[1]),parseFloat(u[2]),parseFloat(u[3])),u.length>=7?(la.setRGB(parseFloat(u[4]),parseFloat(u[5]),parseFloat(u[6]),Ne),e.colors.push(la.r,la.g,la.b)):e.colors.push(void 0,void 0,void 0);break;case"vn":e.normals.push(parseFloat(u[1]),parseFloat(u[2]),parseFloat(u[3]));break;case"vt":e.uvs.push(parseFloat(u[1]),parseFloat(u[2]));break}}else if(h==="f"){const d=l.slice(1).trim().split(Vh),f=[];for(let _=0,m=d.length;_<m;_++){const p=d[_];if(p.length>0){const P=p.split("/");f.push(P)}}const g=f[0];for(let _=1,m=f.length-1;_<m;_++){const p=f[_],P=f[_+1];e.addFace(g[0],p[0],P[0],g[1],p[1],P[1],g[2],p[2],P[2])}}else if(h==="l"){const u=l.substring(1).trim().split(" ");let d=[];const f=[];if(l.indexOf("/")===-1)d=u;else for(let g=0,_=u.length;g<_;g++){const m=u[g].split("/");m[0]!==""&&d.push(m[0]),m[1]!==""&&f.push(m[1])}e.addLineGeometry(d,f)}else if(h==="p"){const d=l.slice(1).trim().split(" ");e.addPointGeometry(d)}else if((s=Hv.exec(l))!==null){const u=(" "+s[0].slice(1).trim()).slice(1);e.startObject(u)}else if(Wv.test(l))e.object.startMaterial(l.substring(7).trim(),e.materialLibraries);else if(Gv.test(l))e.materialLibraries.push(l.substring(7).trim());else if(Xv.test(l))console.warn('THREE.OBJLoader: Rendering identifier "usemap" not supported. Textures must be defined in MTL files.');else if(h==="s"){if(s=l.split(" "),s.length>1){const d=s[1].trim().toLowerCase();e.object.smooth=d!=="0"&&d!=="off"}else e.object.smooth=!0;const u=e.object.currentMaterial();u&&(u.smooth=e.object.smooth)}else{if(l==="\0")continue;console.warn('THREE.OBJLoader: Unexpected line: "'+l+'"')}}e.finalize();const r=new ke;if(r.materialLibraries=[].concat(e.materialLibraries),!(e.objects.length===1&&e.objects[0].geometry.vertices.length===0)===!0)for(let o=0,c=e.objects.length;o<c;o++){const l=e.objects[o],h=l.geometry,u=l.materials,d=h.type==="Line",f=h.type==="Points";let g=!1;if(h.vertices.length===0)continue;const _=new Le;_.setAttribute("position",new ie(h.vertices,3)),h.normals.length>0&&_.setAttribute("normal",new ie(h.normals,3)),h.colors.length>0&&(g=!0,_.setAttribute("color",new ie(h.colors,3))),h.hasUVIndices===!0&&_.setAttribute("uv",new ie(h.uvs,2));const m=[];for(let P=0,w=u.length;P<w;P++){const y=u[P],N=y.name+"_"+y.smooth+"_"+g;let C=e.materials[N];if(this.materials!==null){if(C=this.materials.create(y.name),d&&C&&!(C instanceof zn)){const L=new zn;Hn.prototype.copy.call(L,C),L.color.copy(C.color),C=L}else if(f&&C&&!(C instanceof or)){const L=new or({size:10,sizeAttenuation:!1});Hn.prototype.copy.call(L,C),L.color.copy(C.color),L.map=C.map,C=L}}C===void 0&&(d?C=new zn:f?C=new or({size:1,sizeAttenuation:!1}):C=new Ts,C.name=y.name,C.flatShading=!y.smooth,C.vertexColors=g,e.materials[N]=C),m.push(C)}let p;if(m.length>1){for(let P=0,w=u.length;P<w;P++){const y=u[P];_.addGroup(y.groupStart,y.groupCount,P)}d?p=new Ta(_,m):f?p=new Uo(_,m):p=new ge(_,m)}else d?p=new Ta(_,m[0]):f?p=new Uo(_,m[0]):p=new ge(_,m[0]);p.name=l.name,r.add(p)}else if(e.vertices.length>0){const o=new or({size:1,sizeAttenuation:!1}),c=new Le;c.setAttribute("position",new ie(e.vertices,3)),e.colors.length>0&&e.colors[0]!==void 0&&(c.setAttribute("color",new ie(e.colors,3)),o.vertexColors=!0);const l=new Uo(c,o);r.add(l)}return r}}class jv extends mi{constructor(t){super(t)}load(t,e,n,s){const r=this,a=new Xa(this.manager);a.setPath(this.path),a.setResponseType("arraybuffer"),a.setRequestHeader(this.requestHeader),a.setWithCredentials(this.withCredentials),a.load(t,function(o){try{e(r.parse(o))}catch(c){s?s(c):console.error(c),r.manager.itemError(t)}},n,s)}parse(t){function e(l){const h=new DataView(l),u=32/8*3+32/8*3*3+16/8,d=h.getUint32(80,!0);if(80+32/8+d*u===h.byteLength)return!0;const g=[115,111,108,105,100];for(let _=0;_<5;_++)if(n(g,h,_))return!1;return!0}function n(l,h,u){for(let d=0,f=l.length;d<f;d++)if(l[d]!==h.getUint8(u+d))return!1;return!0}function s(l){const h=new DataView(l),u=h.getUint32(80,!0);let d,f,g,_=!1,m,p,P,w,y;for(let F=0;F<70;F++)h.getUint32(F,!1)==1129270351&&h.getUint8(F+4)==82&&h.getUint8(F+5)==61&&(_=!0,m=new Float32Array(u*3*3),p=h.getUint8(F+6)/255,P=h.getUint8(F+7)/255,w=h.getUint8(F+8)/255,y=h.getUint8(F+9)/255);const N=84,C=50,L=new Le,I=new Float32Array(u*3*3),M=new Float32Array(u*3*3),b=new Jt;for(let F=0;F<u;F++){const k=N+F*C,H=h.getFloat32(k,!0),Z=h.getFloat32(k+4,!0),tt=h.getFloat32(k+8,!0);if(_){const O=h.getUint16(k+48,!0);(O&32768)===0?(d=(O&31)/31,f=(O>>5&31)/31,g=(O>>10&31)/31):(d=p,f=P,g=w)}for(let O=1;O<=3;O++){const et=k+O*12,W=F*3*3+(O-1)*3;I[W]=h.getFloat32(et,!0),I[W+1]=h.getFloat32(et+4,!0),I[W+2]=h.getFloat32(et+8,!0),M[W]=H,M[W+1]=Z,M[W+2]=tt,_&&(b.setRGB(d,f,g,Ne),m[W]=b.r,m[W+1]=b.g,m[W+2]=b.b)}}return L.setAttribute("position",new bn(I,3)),L.setAttribute("normal",new bn(M,3)),_&&(L.setAttribute("color",new bn(m,3)),L.hasColors=!0,L.alpha=y),L}function r(l){const h=new Le,u=/solid([\s\S]*?)endsolid/g,d=/facet([\s\S]*?)endfacet/g,f=/solid\s(.+)/;let g=0;const _=/[\s]+([+-]?(?:\d*)(?:\.\d*)?(?:[eE][+-]?\d+)?)/.source,m=new RegExp("vertex"+_+_+_,"g"),p=new RegExp("normal"+_+_+_,"g"),P=[],w=[],y=[],N=new D;let C,L=0,I=0,M=0;for(;(C=u.exec(l))!==null;){I=M;const b=C[0],F=(C=f.exec(b))!==null?C[1]:"";for(y.push(F);(C=d.exec(b))!==null;){let Z=0,tt=0;const O=C[0];for(;(C=p.exec(O))!==null;)N.x=parseFloat(C[1]),N.y=parseFloat(C[2]),N.z=parseFloat(C[3]),tt++;for(;(C=m.exec(O))!==null;)P.push(parseFloat(C[1]),parseFloat(C[2]),parseFloat(C[3])),w.push(N.x,N.y,N.z),Z++,M++;tt!==1&&console.error("THREE.STLLoader: Something isn't right with the normal of face number "+g),Z!==3&&console.error("THREE.STLLoader: Something isn't right with the vertices of face number "+g),g++}const k=I,H=M-I;h.userData.groupNames=y,h.addGroup(k,H,L),L++}return h.setAttribute("position",new ie(P,3)),h.setAttribute("normal",new ie(w,3)),h}function a(l){return typeof l!="string"?new TextDecoder().decode(l):l}function o(l){if(typeof l=="string"){const h=new Uint8Array(l.length);for(let u=0;u<l.length;u++)h[u]=l.charCodeAt(u)&255;return h.buffer||h}else return l}const c=o(t);return e(c)?s(c):r(a(t))}}class Xh extends _v{constructor(t){super(t)}parse(t){function e(O){switch(O.image_type){case d:case _:if(O.colormap_length>256||O.colormap_size!==24||O.colormap_type!==1)throw new Error("THREE.TGALoader: Invalid type colormap data for indexed type.");break;case f:case g:case m:case p:if(O.colormap_type)throw new Error("THREE.TGALoader: Invalid type colormap data for colormap type.");break;case u:throw new Error("THREE.TGALoader: No data.");default:throw new Error("THREE.TGALoader: Invalid type "+O.image_type)}if(O.width<=0||O.height<=0)throw new Error("THREE.TGALoader: Invalid image size.");if(O.pixel_size!==8&&O.pixel_size!==16&&O.pixel_size!==24&&O.pixel_size!==32)throw new Error("THREE.TGALoader: Invalid pixel size "+O.pixel_size)}function n(O,et,W,lt,pt){let mt,Rt;const wt=W.pixel_size>>3,q=W.width*W.height*wt;if(et&&(Rt=pt.subarray(lt,lt+=W.colormap_length*(W.colormap_size>>3))),O){mt=new Uint8Array(q);let J,nt,it,vt=0;const zt=new Uint8Array(wt);for(;vt<q;)if(J=pt[lt++],nt=(J&127)+1,J&128){for(it=0;it<wt;++it)zt[it]=pt[lt++];for(it=0;it<nt;++it)mt.set(zt,vt+it*wt);vt+=wt*nt}else{for(nt*=wt,it=0;it<nt;++it)mt[vt+it]=pt[lt++];vt+=nt}}else mt=pt.subarray(lt,lt+=et?W.width*W.height:q);return{pixel_data:mt,palettes:Rt}}function s(O,et,W,lt,pt,mt,Rt,wt,q){const J=q;let nt,it=0,vt,zt;const Qt=b.width;for(zt=et;zt!==lt;zt+=W)for(vt=pt;vt!==Rt;vt+=mt,it++)nt=wt[it],O[(vt+Qt*zt)*4+3]=255,O[(vt+Qt*zt)*4+2]=J[nt*3+0],O[(vt+Qt*zt)*4+1]=J[nt*3+1],O[(vt+Qt*zt)*4+0]=J[nt*3+2];return O}function r(O,et,W,lt,pt,mt,Rt,wt){let q,J=0,nt,it;const vt=b.width;for(it=et;it!==lt;it+=W)for(nt=pt;nt!==Rt;nt+=mt,J+=2)q=wt[J+0]+(wt[J+1]<<8),O[(nt+vt*it)*4+0]=(q&31744)>>7,O[(nt+vt*it)*4+1]=(q&992)>>2,O[(nt+vt*it)*4+2]=(q&31)<<3,O[(nt+vt*it)*4+3]=q&32768?0:255;return O}function a(O,et,W,lt,pt,mt,Rt,wt){let q=0,J,nt;const it=b.width;for(nt=et;nt!==lt;nt+=W)for(J=pt;J!==Rt;J+=mt,q+=3)O[(J+it*nt)*4+3]=255,O[(J+it*nt)*4+2]=wt[q+0],O[(J+it*nt)*4+1]=wt[q+1],O[(J+it*nt)*4+0]=wt[q+2];return O}function o(O,et,W,lt,pt,mt,Rt,wt){let q=0,J,nt;const it=b.width;for(nt=et;nt!==lt;nt+=W)for(J=pt;J!==Rt;J+=mt,q+=4)O[(J+it*nt)*4+2]=wt[q+0],O[(J+it*nt)*4+1]=wt[q+1],O[(J+it*nt)*4+0]=wt[q+2],O[(J+it*nt)*4+3]=wt[q+3];return O}function c(O,et,W,lt,pt,mt,Rt,wt){let q,J=0,nt,it;const vt=b.width;for(it=et;it!==lt;it+=W)for(nt=pt;nt!==Rt;nt+=mt,J++)q=wt[J],O[(nt+vt*it)*4+0]=q,O[(nt+vt*it)*4+1]=q,O[(nt+vt*it)*4+2]=q,O[(nt+vt*it)*4+3]=255;return O}function l(O,et,W,lt,pt,mt,Rt,wt){let q=0,J,nt;const it=b.width;for(nt=et;nt!==lt;nt+=W)for(J=pt;J!==Rt;J+=mt,q+=2)O[(J+it*nt)*4+0]=wt[q+0],O[(J+it*nt)*4+1]=wt[q+0],O[(J+it*nt)*4+2]=wt[q+0],O[(J+it*nt)*4+3]=wt[q+1];return O}function h(O,et,W,lt,pt){let mt,Rt,wt,q,J,nt;switch((b.flags&P)>>w){default:case C:mt=0,wt=1,J=et,Rt=0,q=1,nt=W;break;case y:mt=0,wt=1,J=et,Rt=W-1,q=-1,nt=-1;break;case L:mt=et-1,wt=-1,J=-1,Rt=0,q=1,nt=W;break;case N:mt=et-1,wt=-1,J=-1,Rt=W-1,q=-1,nt=-1;break}if(H)switch(b.pixel_size){case 8:c(O,Rt,q,nt,mt,wt,J,lt);break;case 16:l(O,Rt,q,nt,mt,wt,J,lt);break;default:throw new Error("THREE.TGALoader: Format not supported.")}else switch(b.pixel_size){case 8:s(O,Rt,q,nt,mt,wt,J,lt,pt);break;case 16:r(O,Rt,q,nt,mt,wt,J,lt);break;case 24:a(O,Rt,q,nt,mt,wt,J,lt);break;case 32:o(O,Rt,q,nt,mt,wt,J,lt);break;default:throw new Error("THREE.TGALoader: Format not supported.")}return O}const u=0,d=1,f=2,g=3,_=9,m=10,p=11,P=48,w=4,y=0,N=1,C=2,L=3;if(t.length<19)throw new Error("THREE.TGALoader: Not enough data to contain header.");let I=0;const M=new Uint8Array(t),b={id_length:M[I++],colormap_type:M[I++],image_type:M[I++],colormap_index:M[I++]|M[I++]<<8,colormap_length:M[I++]|M[I++]<<8,colormap_size:M[I++],origin:[M[I++]|M[I++]<<8,M[I++]|M[I++]<<8],width:M[I++]|M[I++]<<8,height:M[I++]|M[I++]<<8,pixel_size:M[I++],flags:M[I++]};if(e(b),b.id_length+I>t.length)throw new Error("THREE.TGALoader: No data.");I+=b.id_length;let F=!1,k=!1,H=!1;switch(b.image_type){case _:F=!0,k=!0;break;case d:k=!0;break;case m:F=!0;break;case f:break;case p:F=!0,H=!0;break;case g:H=!0;break}const Z=new Uint8Array(b.width*b.height*4),tt=n(F,k,b,I,M);return h(Z,b.width,b.height,tt.pixel_data,tt.palettes),{data:Z,width:b.width,height:b.height,flipY:!0,generateMipmaps:!0,minFilter:li}}}class Yv extends mi{load(t,e,n,s){const r=this,a=r.path===""?Gu.extractUrlBase(t):r.path,o=new Xa(r.manager);o.setPath(r.path),o.setRequestHeader(r.requestHeader),o.setWithCredentials(r.withCredentials),o.load(t,function(c){try{e(r.parse(c,a))}catch(l){s?s(l):console.error(l),r.manager.itemError(t)}},n,s)}parse(t,e){function n(x,v){const T=[],E=x.childNodes;for(let R=0,K=E.length;R<K;R++){const st=E[R];st.nodeName===v&&T.push(st)}return T}function s(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),T=new Array(v.length);for(let E=0,R=v.length;E<R;E++)T[E]=v[E];return T}function r(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),T=new Array(v.length);for(let E=0,R=v.length;E<R;E++)T[E]=parseFloat(v[E]);return T}function a(x){if(x.length===0)return[];const v=x.trim().split(/\s+/),T=new Array(v.length);for(let E=0,R=v.length;E<R;E++)T[E]=parseInt(v[E]);return T}function o(x){return x.substring(1)}function c(){return"three_default_"+xd++}function l(x){return Object.keys(x).length===0}function h(x){return{unit:u(n(x,"unit")[0]),upAxis:d(n(x,"up_axis")[0])}}function u(x){return x!==void 0&&x.hasAttribute("meter")===!0?parseFloat(x.getAttribute("meter")):1}function d(x){return x!==void 0?x.textContent:"Y_UP"}function f(x,v,T,E){const R=n(x,v)[0];if(R!==void 0){const K=n(R,T);for(let st=0;st<K.length;st++)E(K[st])}}function g(x,v){for(const T in x){const E=x[T];E.build=v(x[T])}}function _(x,v){return x.build!==void 0||(x.build=v(x)),x.build}function m(x){const v={sources:{},samplers:{},channels:{}};let T=!1;for(let E=0,R=x.childNodes.length;E<R;E++){const K=x.childNodes[E];if(K.nodeType!==1)continue;let st;switch(K.nodeName){case"source":st=K.getAttribute("id"),v.sources[st]=Q(K);break;case"sampler":st=K.getAttribute("id"),v.samplers[st]=p(K);break;case"channel":st=K.getAttribute("target"),v.channels[st]=P(K);break;case"animation":m(K),T=!0;break;default:console.log(K)}}T===!1&&(jt.animations[x.getAttribute("id")||Ri.generateUUID()]=v)}function p(x){const v={inputs:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"input":const K=o(R.getAttribute("source")),st=R.getAttribute("semantic");v.inputs[st]=K;break}}return v}function P(x){const v={};let E=x.getAttribute("target").split("/");const R=E.shift();let K=E.shift();const st=K.indexOf("(")!==-1,Tt=K.indexOf(".")!==-1;if(Tt)E=K.split("."),K=E.shift(),v.member=E.shift();else if(st){const gt=K.split("(");K=gt.shift();for(let St=0;St<gt.length;St++)gt[St]=parseInt(gt[St].replace(/\)/,""));v.indices=gt}return v.id=R,v.sid=K,v.arraySyntax=st,v.memberSyntax=Tt,v.sampler=o(x.getAttribute("source")),v}function w(x){const v=[],T=x.channels,E=x.samplers,R=x.sources;for(const K in T)if(T.hasOwnProperty(K)){const st=T[K],Tt=E[st.sampler],gt=Tt.inputs.INPUT,St=Tt.inputs.OUTPUT,Bt=R[gt],ut=R[St],kt=N(st,Bt,ut);b(kt,v)}return v}function y(x){return _(jt.animations[x],w)}function N(x,v,T){const E=jt.nodes[x.id],R=Be(E.id),K=E.transforms[x.sid],st=E.matrix.clone().transpose();let Tt,gt,St,Bt,ut,kt;const Nt={};switch(K){case"matrix":for(St=0,Bt=v.array.length;St<Bt;St++)if(Tt=v.array[St],gt=St*T.stride,Nt[Tt]===void 0&&(Nt[Tt]={}),x.arraySyntax===!0){const Ue=T.array[gt],Se=x.indices[0]+4*x.indices[1];Nt[Tt][Se]=Ue}else for(ut=0,kt=T.stride;ut<kt;ut++)Nt[Tt][ut]=T.array[gt+ut];break;case"translate":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',K);break;case"rotate":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',K);break;case"scale":console.warn('THREE.ColladaLoader: Animation transform type "%s" not yet implemented.',K);break}const Gt=C(Nt,st);return{name:R.uuid,keyframes:Gt}}function C(x,v){const T=[];for(const R in x)T.push({time:parseFloat(R),value:x[R]});T.sort(E);for(let R=0;R<16;R++)F(T,R,v.elements[R]);return T;function E(R,K){return R.time-K.time}}const L=new D,I=new D,M=new Vn;function b(x,v){const T=x.keyframes,E=x.name,R=[],K=[],st=[],Tt=[];for(let gt=0,St=T.length;gt<St;gt++){const Bt=T[gt],ut=Bt.time,kt=Bt.value;B.fromArray(kt).transpose(),B.decompose(L,M,I),R.push(ut),K.push(L.x,L.y,L.z),st.push(M.x,M.y,M.z,M.w),Tt.push(I.x,I.y,I.z)}return K.length>0&&v.push(new Fs(E+".position",R,K)),st.length>0&&v.push(new Sr(E+".quaternion",R,st)),Tt.length>0&&v.push(new Fs(E+".scale",R,Tt)),v}function F(x,v,T){let E,R=!0,K,st;for(K=0,st=x.length;K<st;K++)E=x[K],E.value[v]===void 0?E.value[v]=null:R=!1;if(R===!0)for(K=0,st=x.length;K<st;K++)E=x[K],E.value[v]=T;else k(x,v)}function k(x,v){let T,E;for(let R=0,K=x.length;R<K;R++){const st=x[R];if(st.value[v]===null){if(T=H(x,R,v),E=Z(x,R,v),T===null){st.value[v]=E.value[v];continue}if(E===null){st.value[v]=T.value[v];continue}tt(st,T,E,v)}}}function H(x,v,T){for(;v>=0;){const E=x[v];if(E.value[T]!==null)return E;v--}return null}function Z(x,v,T){for(;v<x.length;){const E=x[v];if(E.value[T]!==null)return E;v++}return null}function tt(x,v,T,E){if(T.time-v.time===0){x.value[E]=v.value[E];return}x.value[E]=(x.time-v.time)*(T.value[E]-v.value[E])/(T.time-v.time)+v.value[E]}function O(x){const v={name:x.getAttribute("id")||"default",start:parseFloat(x.getAttribute("start")||0),end:parseFloat(x.getAttribute("end")||0),animations:[]};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"instance_animation":v.animations.push(o(R.getAttribute("url")));break}}jt.clips[x.getAttribute("id")]=v}function et(x){const v=[],T=x.name,E=x.end-x.start||-1,R=x.animations;for(let K=0,st=R.length;K<st;K++){const Tt=y(R[K]);for(let gt=0,St=Tt.length;gt<St;gt++)v.push(Tt[gt])}return new Lh(T,E,v)}function W(x){return _(jt.clips[x],et)}function lt(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"skin":v.id=o(R.getAttribute("source")),v.skin=pt(R);break;case"morph":v.id=o(R.getAttribute("source")),console.warn("THREE.ColladaLoader: Morph target animation not supported yet.");break}}jt.controllers[x.getAttribute("id")]=v}function pt(x){const v={sources:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"bind_shape_matrix":v.bindShapeMatrix=r(R.textContent);break;case"source":const K=R.getAttribute("id");v.sources[K]=Q(R);break;case"joints":v.joints=mt(R);break;case"vertex_weights":v.vertexWeights=Rt(R);break}}return v}function mt(x){const v={inputs:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"input":const K=R.getAttribute("semantic"),st=o(R.getAttribute("source"));v.inputs[K]=st;break}}return v}function Rt(x){const v={inputs:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"input":const K=R.getAttribute("semantic"),st=o(R.getAttribute("source")),Tt=parseInt(R.getAttribute("offset"));v.inputs[K]={id:st,offset:Tt};break;case"vcount":v.vcount=a(R.textContent);break;case"v":v.v=a(R.textContent);break}}return v}function wt(x){const v={id:x.id},T=jt.geometries[v.id];return x.skin!==void 0&&(v.skin=q(x.skin),T.sources.skinIndices=v.skin.indices,T.sources.skinWeights=v.skin.weights),v}function q(x){const T={joints:[],indices:{array:[],stride:4},weights:{array:[],stride:4}},E=x.sources,R=x.vertexWeights,K=R.vcount,st=R.v,Tt=R.inputs.JOINT.offset,gt=R.inputs.WEIGHT.offset,St=x.sources[x.joints.inputs.JOINT],Bt=x.sources[x.joints.inputs.INV_BIND_MATRIX],ut=E[R.inputs.WEIGHT.id].array;let kt=0,Nt,Gt,Vt;for(Nt=0,Vt=K.length;Nt<Vt;Nt++){const Se=K[Nt],ve=[];for(Gt=0;Gt<Se;Gt++){const xe=st[kt+Tt],Qn=st[kt+gt],hn=ut[Qn];ve.push({index:xe,weight:hn}),kt+=2}for(ve.sort(Ue),Gt=0;Gt<4;Gt++){const xe=ve[Gt];xe!==void 0?(T.indices.array.push(xe.index),T.weights.array.push(xe.weight)):(T.indices.array.push(0),T.weights.array.push(0))}}for(x.bindShapeMatrix?T.bindMatrix=new Yt().fromArray(x.bindShapeMatrix).transpose():T.bindMatrix=new Yt().identity(),Nt=0,Vt=St.array.length;Nt<Vt;Nt++){const Se=St.array[Nt],ve=new Yt().fromArray(Bt.array,Nt*Bt.stride).transpose();T.joints.push({name:Se,boneInverse:ve})}return T;function Ue(Se,ve){return ve.weight-Se.weight}}function J(x){return _(jt.controllers[x],wt)}function nt(x){const v={init_from:n(x,"init_from")[0].textContent};jt.images[x.getAttribute("id")]=v}function it(x){return x.build!==void 0?x.build:x.init_from}function vt(x){const v=jt.images[x];return v!==void 0?_(v,it):(console.warn("THREE.ColladaLoader: Couldn't find image with ID:",x),null)}function zt(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"profile_COMMON":v.profile=Qt(R);break}}jt.effects[x.getAttribute("id")]=v}function Qt(x){const v={surfaces:{},samplers:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"newparam":Re(R,v);break;case"technique":v.technique=G(R);break;case"extra":v.extra=Ht(R);break}}return v}function Re(x,v){const T=x.getAttribute("sid");for(let E=0,R=x.childNodes.length;E<R;E++){const K=x.childNodes[E];if(K.nodeType===1)switch(K.nodeName){case"surface":v.surfaces[T]=ue(K);break;case"sampler2D":v.samplers[T]=Ie(K);break}}}function ue(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"init_from":v.init_from=R.textContent;break}}return v}function Ie(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"source":v.source=R.textContent;break}}return v}function G(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"constant":case"lambert":case"blinn":case"phong":v.type=R.nodeName,v.parameters=on(R);break;case"extra":v.extra=Ht(R);break}}return v}function on(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"emission":case"diffuse":case"specular":case"bump":case"ambient":case"shininess":case"transparency":v[R.nodeName]=oe(R);break;case"transparent":v[R.nodeName]={opaque:R.hasAttribute("opaque")?R.getAttribute("opaque"):"A_ONE",data:oe(R)};break}}return v}function oe(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"color":v[R.nodeName]=r(R.textContent);break;case"float":v[R.nodeName]=parseFloat(R.textContent);break;case"texture":v[R.nodeName]={id:R.getAttribute("texture"),extra:ce(R)};break}}return v}function ce(x){const v={technique:{}};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"extra":Wt(R,v);break}}return v}function Wt(x,v){for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"technique":Ae(R,v);break}}}function Ae(x,v){for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"repeatU":case"repeatV":case"offsetU":case"offsetV":v.technique[R.nodeName]=parseFloat(R.textContent);break;case"wrapU":case"wrapV":R.textContent.toUpperCase()==="TRUE"?v.technique[R.nodeName]=1:R.textContent.toUpperCase()==="FALSE"?v.technique[R.nodeName]=0:v.technique[R.nodeName]=parseInt(R.textContent);break;case"bump":v[R.nodeName]=S(R);break}}}function Ht(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"technique":v.technique=U(R);break}}return v}function U(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"double_sided":v[R.nodeName]=parseInt(R.textContent);break;case"bump":v[R.nodeName]=S(R);break}}return v}function S(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"texture":v[R.nodeName]={id:R.getAttribute("texture"),texcoord:R.getAttribute("texcoord"),extra:ce(R)};break}}return v}function j(x){return x}function at(x){return _(jt.effects[x],j)}function ht(x){const v={name:x.getAttribute("name")};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"instance_effect":v.url=o(R.getAttribute("url"));break}}jt.materials[x.getAttribute("id")]=v}function rt(x){let v,T=x.slice((x.lastIndexOf(".")-1>>>0)+2);switch(T=T.toLowerCase(),T){case"tga":v=An;break;default:v=In}return v}function Ft(x){const v=at(x.url),T=v.profile.technique;let E;switch(T.type){case"phong":case"blinn":E=new Ts;break;case"lambert":E=new av;break;default:E=new Ke;break}E.name=x.name||"";function R(gt,St=null){const Bt=v.profile.samplers[gt.id];let ut=null;if(Bt!==void 0){const kt=v.profile.surfaces[Bt.source];ut=vt(kt.init_from)}else console.warn("THREE.ColladaLoader: Undefined sampler. Access image directly (see #12530)."),ut=vt(gt.id);if(ut!==null){const kt=rt(ut);if(kt!==void 0){const Nt=kt.load(ut),Gt=gt.extra;if(Gt!==void 0&&Gt.technique!==void 0&&l(Gt.technique)===!1){const Vt=Gt.technique;Nt.wrapS=Vt.wrapU?Yi:Bn,Nt.wrapT=Vt.wrapV?Yi:Bn,Nt.offset.set(Vt.offsetU||0,Vt.offsetV||0),Nt.repeat.set(Vt.repeatU||1,Vt.repeatV||1)}else Nt.wrapS=Yi,Nt.wrapT=Yi;return St!==null&&(Nt.colorSpace=St),Nt}else return console.warn("THREE.ColladaLoader: Loader for texture %s not found.",ut),null}else return console.warn("THREE.ColladaLoader: Couldn't create texture with ID:",gt.id),null}const K=T.parameters;for(const gt in K){const St=K[gt];switch(gt){case"diffuse":St.color&&E.color.fromArray(St.color),St.texture&&(E.map=R(St.texture,Ne));break;case"specular":St.color&&E.specular&&E.specular.fromArray(St.color),St.texture&&(E.specularMap=R(St.texture));break;case"bump":St.texture&&(E.normalMap=R(St.texture));break;case"ambient":St.texture&&(E.lightMap=R(St.texture,Ne));break;case"shininess":St.float&&E.shininess&&(E.shininess=St.float);break;case"emission":St.color&&E.emissive&&E.emissive.fromArray(St.color),St.texture&&(E.emissiveMap=R(St.texture,Ne));break}}le.toWorkingColorSpace(E.color,Ne),E.specular&&le.toWorkingColorSpace(E.specular,Ne),E.emissive&&le.toWorkingColorSpace(E.emissive,Ne);let st=K.transparent,Tt=K.transparency;if(Tt===void 0&&st&&(Tt={float:1}),st===void 0&&Tt&&(st={opaque:"A_ONE",data:{color:[1,1,1,1]}}),st&&Tt)if(st.data.texture)E.transparent=!0;else{const gt=st.data.color;switch(st.opaque){case"A_ONE":E.opacity=gt[3]*Tt.float;break;case"RGB_ZERO":E.opacity=1-gt[0]*Tt.float;break;case"A_ZERO":E.opacity=1-gt[3]*Tt.float;break;case"RGB_ONE":E.opacity=gt[0]*Tt.float;break;default:console.warn('THREE.ColladaLoader: Invalid opaque type "%s" of transparent tag.',st.opaque)}E.opacity<1&&(E.transparent=!0)}if(T.extra!==void 0&&T.extra.technique!==void 0){const gt=T.extra.technique;for(const St in gt){const Bt=gt[St];switch(St){case"double_sided":E.side=Bt===1?dn:di;break;case"bump":E.normalMap=R(Bt.texture),E.normalScale=new At(1,1);break}}}return E}function Mt(x){return _(jt.materials[x],Ft)}function Ct(x){const v={name:x.getAttribute("name")};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"optics":v.optics=de(R);break}}jt.cameras[x.getAttribute("id")]=v}function de(x){for(let v=0;v<x.childNodes.length;v++){const T=x.childNodes[v];switch(T.nodeName){case"technique_common":return ft(T)}}return{}}function ft(x){const v={};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];switch(E.nodeName){case"perspective":case"orthographic":v.technique=E.nodeName,v.parameters=Pt(E);break}}return v}function Pt(x){const v={};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];switch(E.nodeName){case"xfov":case"yfov":case"xmag":case"ymag":case"znear":case"zfar":case"aspect_ratio":v[E.nodeName]=parseFloat(E.textContent);break}}return v}function Xt(x){let v;switch(x.optics.technique){case"perspective":v=new tn(x.optics.parameters.yfov,x.optics.parameters.aspect_ratio,x.optics.parameters.znear,x.optics.parameters.zfar);break;case"orthographic":let T=x.optics.parameters.ymag,E=x.optics.parameters.xmag;const R=x.optics.parameters.aspect_ratio;E=E===void 0?T*R:E,T=T===void 0?E/R:T,E*=.5,T*=.5,v=new $c(-E,E,T,-T,x.optics.parameters.znear,x.optics.parameters.zfar);break;default:v=new tn;break}return v.name=x.name||"",v}function $t(x){const v=jt.cameras[x];return v!==void 0?_(v,Xt):(console.warn("THREE.ColladaLoader: Couldn't find camera with ID:",x),null)}function Lt(x){let v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"technique_common":v=he(R);break}}jt.lights[x.getAttribute("id")]=v}function he(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"directional":case"point":case"spot":case"ambient":v.technique=R.nodeName,v.parameters=ne(R)}}return v}function ne(x){const v={};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"color":const K=r(R.textContent);v.color=new Jt().fromArray(K),le.toWorkingColorSpace(v.color,Ne);break;case"falloff_angle":v.falloffAngle=parseFloat(R.textContent);break;case"quadratic_attenuation":const st=parseFloat(R.textContent);v.distance=st?Math.sqrt(1/st):0;break}}return v}function Me(x){let v;switch(x.technique){case"directional":v=new Hu;break;case"point":v=new bv;break;case"spot":v=new yv;break;case"ambient":v=new Ev;break}return x.parameters.color&&v.color.copy(x.parameters.color),x.parameters.distance&&(v.distance=x.parameters.distance),v}function z(x){const v=jt.lights[x];return v!==void 0?_(v,Me):(console.warn("THREE.ColladaLoader: Couldn't find light with ID:",x),null)}function xt(x){const v={name:x.getAttribute("name"),sources:{},vertices:{},primitives:[]},T=n(x,"mesh")[0];if(T!==void 0){for(let E=0;E<T.childNodes.length;E++){const R=T.childNodes[E];if(R.nodeType!==1)continue;const K=R.getAttribute("id");switch(R.nodeName){case"source":v.sources[K]=Q(R);break;case"vertices":v.vertices=ot(R);break;case"polygons":console.warn("THREE.ColladaLoader: Unsupported primitive type: ",R.nodeName);break;case"lines":case"linestrips":case"polylist":case"triangles":v.primitives.push(Et(R));break;default:console.log(R)}}jt.geometries[x.getAttribute("id")]=v}}function Q(x){const v={array:[],stride:3};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"float_array":v.array=r(E.textContent);break;case"Name_array":v.array=s(E.textContent);break;case"technique_common":const R=n(E,"accessor")[0];R!==void 0&&(v.stride=parseInt(R.getAttribute("stride")));break}}return v}function ot(x){const v={};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];E.nodeType===1&&(v[E.getAttribute("semantic")]=o(E.getAttribute("source")))}return v}function Et(x){const v={type:x.nodeName,material:x.getAttribute("material"),count:parseInt(x.getAttribute("count")),inputs:{},stride:0,hasUV:!1};for(let T=0,E=x.childNodes.length;T<E;T++){const R=x.childNodes[T];if(R.nodeType===1)switch(R.nodeName){case"input":const K=o(R.getAttribute("source")),st=R.getAttribute("semantic"),Tt=parseInt(R.getAttribute("offset")),gt=parseInt(R.getAttribute("set")),St=gt>0?st+gt:st;v.inputs[St]={id:K,offset:Tt},v.stride=Math.max(v.stride,Tt+1),st==="TEXCOORD"&&(v.hasUV=!0);break;case"vcount":v.vcount=a(R.textContent);break;case"p":v.p=a(R.textContent);break}}return v}function bt(x){const v={};for(let T=0;T<x.length;T++){const E=x[T];v[E.type]===void 0&&(v[E.type]=[]),v[E.type].push(E)}return v}function te(x){let v=0;for(let T=0,E=x.length;T<E;T++)x[T].hasUV===!0&&v++;v>0&&v<x.length&&(x.uvsNeedsFix=!0)}function Pe(x){const v={},T=x.sources,E=x.vertices,R=x.primitives;if(R.length===0)return{};const K=bt(R);for(const st in K){const Tt=K[st];te(Tt),v[st]=qe(Tt,T,E)}return v}function qe(x,v,T){const E={},R={array:[],stride:0},K={array:[],stride:0},st={array:[],stride:0},Tt={array:[],stride:0},gt={array:[],stride:0},St={array:[],stride:4},Bt={array:[],stride:4},ut=new Le,kt=[];let Nt=0;for(let Gt=0;Gt<x.length;Gt++){const Vt=x[Gt],Ue=Vt.inputs;let Se=0;switch(Vt.type){case"lines":case"linestrips":Se=Vt.count*2;break;case"triangles":Se=Vt.count*3;break;case"polylist":for(let ve=0;ve<Vt.count;ve++){const xe=Vt.vcount[ve];switch(xe){case 3:Se+=3;break;case 4:Se+=6;break;default:Se+=(xe-2)*3;break}}break;default:console.warn("THREE.ColladaLoader: Unknow primitive type:",Vt.type)}ut.addGroup(Nt,Se,Gt),Nt+=Se,Vt.material&&kt.push(Vt.material);for(const ve in Ue){const xe=Ue[ve];switch(ve){case"VERTEX":for(const Qn in T){const hn=T[Qn];switch(Qn){case"POSITION":const ss=R.array.length;if(se(Vt,v[hn],xe.offset,R.array),R.stride=v[hn].stride,v.skinWeights&&v.skinIndices&&(se(Vt,v.skinIndices,xe.offset,St.array),se(Vt,v.skinWeights,xe.offset,Bt.array)),Vt.hasUV===!1&&x.uvsNeedsFix===!0){const yd=(R.array.length-ss)/R.stride;for(let fl=0;fl<yd;fl++)st.array.push(0,0)}break;case"NORMAL":se(Vt,v[hn],xe.offset,K.array),K.stride=v[hn].stride;break;case"COLOR":se(Vt,v[hn],xe.offset,gt.array),gt.stride=v[hn].stride;break;case"TEXCOORD":se(Vt,v[hn],xe.offset,st.array),st.stride=v[hn].stride;break;case"TEXCOORD1":se(Vt,v[hn],xe.offset,Tt.array),st.stride=v[hn].stride;break;default:console.warn('THREE.ColladaLoader: Semantic "%s" not handled in geometry build process.',Qn)}}break;case"NORMAL":se(Vt,v[xe.id],xe.offset,K.array),K.stride=v[xe.id].stride;break;case"COLOR":se(Vt,v[xe.id],xe.offset,gt.array,!0),gt.stride=v[xe.id].stride;break;case"TEXCOORD":se(Vt,v[xe.id],xe.offset,st.array),st.stride=v[xe.id].stride;break;case"TEXCOORD1":se(Vt,v[xe.id],xe.offset,Tt.array),Tt.stride=v[xe.id].stride;break}}}return R.array.length>0&&ut.setAttribute("position",new ie(R.array,R.stride)),K.array.length>0&&ut.setAttribute("normal",new ie(K.array,K.stride)),gt.array.length>0&&ut.setAttribute("color",new ie(gt.array,gt.stride)),st.array.length>0&&ut.setAttribute("uv",new ie(st.array,st.stride)),Tt.array.length>0&&ut.setAttribute("uv1",new ie(Tt.array,Tt.stride)),St.array.length>0&&ut.setAttribute("skinIndex",new ie(St.array,St.stride)),Bt.array.length>0&&ut.setAttribute("skinWeight",new ie(Bt.array,Bt.stride)),E.data=ut,E.type=x[0].type,E.materialKeys=kt,E}function se(x,v,T,E,R=!1){const K=x.p,st=x.stride,Tt=x.vcount;function gt(ut){let kt=K[ut+T]*Bt;const Nt=kt+Bt;for(;kt<Nt;kt++)E.push(St[kt]);if(R){const Gt=E.length-Bt-1;ki.setRGB(E[Gt+0],E[Gt+1],E[Gt+2],Ne),E[Gt+0]=ki.r,E[Gt+1]=ki.g,E[Gt+2]=ki.b}}const St=v.array,Bt=v.stride;if(x.vcount!==void 0){let ut=0;for(let kt=0,Nt=Tt.length;kt<Nt;kt++){const Gt=Tt[kt];if(Gt===4){const Vt=ut+st*0,Ue=ut+st*1,Se=ut+st*2,ve=ut+st*3;gt(Vt),gt(Ue),gt(ve),gt(Ue),gt(Se),gt(ve)}else if(Gt===3){const Vt=ut+st*0,Ue=ut+st*1,Se=ut+st*2;gt(Vt),gt(Ue),gt(Se)}else if(Gt>4)for(let Vt=1,Ue=Gt-2;Vt<=Ue;Vt++){const Se=ut+st*0,ve=ut+st*Vt,xe=ut+st*(Vt+1);gt(Se),gt(ve),gt(xe)}ut+=st*Gt}}else for(let ut=0,kt=K.length;ut<kt;ut+=st)gt(ut)}function cn(x){return _(jt.geometries[x],Pe)}function Nn(x){const v={name:x.getAttribute("name")||"",joints:{},links:[]};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"technique_common":Zn(E,v);break}}jt.kinematicsModels[x.getAttribute("id")]=v}function Tr(x){return x.build!==void 0?x.build:x}function Ar(x){return _(jt.kinematicsModels[x],Tr)}function Zn(x,v){for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"joint":v.joints[E.getAttribute("sid")]=Ks(E);break;case"link":v.links.push(Js(E));break}}}function Ks(x){let v;for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"prismatic":case"revolute":v=Cr(E);break}}return v}function Cr(x){const v={sid:x.getAttribute("sid"),name:x.getAttribute("name")||"",axis:new D,limits:{min:0,max:0},type:x.nodeName,static:!1,zeroPosition:0,middlePosition:0};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"axis":const R=r(E.textContent);v.axis.fromArray(R);break;case"limits":const K=E.getElementsByTagName("max")[0],st=E.getElementsByTagName("min")[0];v.limits.max=parseFloat(K.textContent),v.limits.min=parseFloat(st.textContent);break}}return v.limits.min>=v.limits.max&&(v.static=!0),v.middlePosition=(v.limits.min+v.limits.max)/2,v}function Js(x){const v={sid:x.getAttribute("sid"),name:x.getAttribute("name")||"",attachments:[],transforms:[]};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"attachment_full":v.attachments.push(ns(E));break;case"matrix":case"translate":case"rotate":v.transforms.push(Zs(E));break}}return v}function ns(x){const v={joint:x.getAttribute("joint").split("/").pop(),transforms:[],links:[]};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"link":v.links.push(Js(E));break;case"matrix":case"translate":case"rotate":v.transforms.push(Zs(E));break}}return v}function Zs(x){const v={type:x.nodeName},T=r(x.textContent);switch(v.type){case"matrix":v.obj=new Yt,v.obj.fromArray(T).transpose();break;case"translate":v.obj=new D,v.obj.fromArray(T);break;case"rotate":v.obj=new D,v.obj.fromArray(T),v.angle=Ri.degToRad(T[3]);break}return v}function is(x){const v={name:x.getAttribute("name")||"",rigidBodies:{}};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"rigid_body":v.rigidBodies[E.getAttribute("name")]={},Rr(E,v.rigidBodies[E.getAttribute("name")]);break}}jt.physicsModels[x.getAttribute("id")]=v}function Rr(x,v){for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"technique_common":Pr(E,v);break}}}function Pr(x,v){for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"inertia":v.inertia=r(E.textContent);break;case"mass":v.mass=r(E.textContent)[0];break}}}function Qa(x){const v={bindJointAxis:[]};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"bind_joint_axis":v.bindJointAxis.push(to(E));break}}jt.kinematicsScenes[o(x.getAttribute("url"))]=v}function to(x){const v={target:x.getAttribute("target").split("/").pop()};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType===1)switch(E.nodeName){case"axis":const R=E.getElementsByTagName("param")[0];v.axis=R.textContent;const K=v.axis.split("inst_").pop().split("axis")[0];v.jointIndex=K.substring(0,K.length-1);break}}return v}function eo(x){return x.build!==void 0?x.build:x}function A(x){return _(jt.kinematicsScenes[x],eo)}function V(){const x=Object.keys(jt.kinematicsModels)[0],v=Object.keys(jt.kinematicsScenes)[0],T=Object.keys(jt.visualScenes)[0];if(x===void 0||v===void 0)return;const E=Ar(x),R=A(v),K=me(T),st=R.bindJointAxis,Tt={};for(let Bt=0,ut=st.length;Bt<ut;Bt++){const kt=st[Bt],Nt=Zt.querySelector('[sid="'+kt.target+'"]');if(Nt){const Gt=Nt.parentElement;gt(kt.jointIndex,Gt)}}function gt(Bt,ut){const kt=ut.getAttribute("name"),Nt=E.joints[Bt];K.traverse(function(Gt){Gt.name===kt&&(Tt[Bt]={object:Gt,transforms:Y(ut),joint:Nt,position:Nt.zeroPosition})})}const St=new Yt;dl={joints:E&&E.joints,getJointValue:function(Bt){const ut=Tt[Bt];if(ut)return ut.position;console.warn("THREE.ColladaLoader: Joint "+Bt+" doesn't exist.")},setJointValue:function(Bt,ut){const kt=Tt[Bt];if(kt){const Nt=kt.joint;if(ut>Nt.limits.max||ut<Nt.limits.min)console.warn("THREE.ColladaLoader: Joint "+Bt+" value "+ut+" outside of limits (min: "+Nt.limits.min+", max: "+Nt.limits.max+").");else if(Nt.static)console.warn("THREE.ColladaLoader: Joint "+Bt+" is static.");else{const Gt=kt.object,Vt=Nt.axis,Ue=kt.transforms;B.identity();for(let Se=0;Se<Ue.length;Se++){const ve=Ue[Se];if(ve.sid&&ve.sid.indexOf(Bt)!==-1)switch(Nt.type){case"revolute":B.multiply(St.makeRotationAxis(Vt,Ri.degToRad(ut)));break;case"prismatic":B.multiply(St.makeTranslation(Vt.x*ut,Vt.y*ut,Vt.z*ut));break;default:console.warn("THREE.ColladaLoader: Unknown joint type: "+Nt.type);break}else switch(ve.type){case"matrix":B.multiply(ve.obj);break;case"translate":B.multiply(St.makeTranslation(ve.obj.x,ve.obj.y,ve.obj.z));break;case"scale":B.scale(ve.obj);break;case"rotate":B.multiply(St.makeRotationAxis(ve.obj,ve.angle));break}}Gt.matrix.copy(B),Gt.matrix.decompose(Gt.position,Gt.quaternion,Gt.scale),Tt[Bt].position=ut}}else console.log("THREE.ColladaLoader: "+Bt+" does not exist.")}}}function Y(x){const v=[],T=Zt.querySelector('[id="'+x.id+'"]');for(let E=0;E<T.childNodes.length;E++){const R=T.childNodes[E];if(R.nodeType!==1)continue;let K,st;switch(R.nodeName){case"matrix":K=r(R.textContent);const Tt=new Yt().fromArray(K).transpose();v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:Tt});break;case"translate":case"scale":K=r(R.textContent),st=new D().fromArray(K),v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:st});break;case"rotate":K=r(R.textContent),st=new D().fromArray(K);const gt=Ri.degToRad(K[3]);v.push({sid:R.getAttribute("sid"),type:R.nodeName,obj:st,angle:gt});break}}return v}function $(x){const v=x.getElementsByTagName("node");for(let T=0;T<v.length;T++){const E=v[T];E.hasAttribute("id")===!1&&E.setAttribute("id",c())}}const B=new Yt,dt=new D;function yt(x){const v={name:x.getAttribute("name")||"",type:x.getAttribute("type"),id:x.getAttribute("id"),sid:x.getAttribute("sid"),matrix:new Yt,nodes:[],instanceCameras:[],instanceControllers:[],instanceLights:[],instanceGeometries:[],instanceNodes:[],transforms:{}};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];if(E.nodeType!==1)continue;let R;switch(E.nodeName){case"node":v.nodes.push(E.getAttribute("id")),yt(E);break;case"instance_camera":v.instanceCameras.push(o(E.getAttribute("url")));break;case"instance_controller":v.instanceControllers.push(Dt(E));break;case"instance_light":v.instanceLights.push(o(E.getAttribute("url")));break;case"instance_geometry":v.instanceGeometries.push(Dt(E));break;case"instance_node":v.instanceNodes.push(o(E.getAttribute("url")));break;case"matrix":R=r(E.textContent),v.matrix.multiply(B.fromArray(R).transpose()),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"translate":R=r(E.textContent),dt.fromArray(R),v.matrix.multiply(B.makeTranslation(dt.x,dt.y,dt.z)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"rotate":R=r(E.textContent);const K=Ri.degToRad(R[3]);v.matrix.multiply(B.makeRotationAxis(dt.fromArray(R),K)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"scale":R=r(E.textContent),v.matrix.scale(dt.fromArray(R)),v.transforms[E.getAttribute("sid")]=E.nodeName;break;case"extra":break;default:console.log(E)}}return Ee(v.id)?console.warn("THREE.ColladaLoader: There is already a node with ID %s. Exclude current node from further processing.",v.id):jt.nodes[v.id]=v,v}function Dt(x){const v={id:o(x.getAttribute("url")),materials:{},skeletons:[]};for(let T=0;T<x.childNodes.length;T++){const E=x.childNodes[T];switch(E.nodeName){case"bind_material":const R=E.getElementsByTagName("instance_material");for(let K=0;K<R.length;K++){const st=R[K],Tt=st.getAttribute("symbol"),gt=st.getAttribute("target");v.materials[Tt]=o(gt)}break;case"skeleton":v.skeletons.push(o(E.textContent));break}}return v}function It(x,v){const T=[],E=[];let R,K,st;for(R=0;R<x.length;R++){const St=x[R];let Bt;if(Ee(St))Bt=Be(St),Kt(Bt,v,T);else if(Dn(St)){const kt=jt.visualScenes[St].children;for(let Nt=0;Nt<kt.length;Nt++){const Gt=kt[Nt];if(Gt.type==="JOINT"){const Vt=Be(Gt.id);Kt(Vt,v,T)}}}else console.error("THREE.ColladaLoader: Unable to find root bone of skeleton with ID:",St)}for(R=0;R<v.length;R++)for(K=0;K<T.length;K++)if(st=T[K],st.bone.name===v[R].name){E[R]=st,st.processed=!0;break}for(R=0;R<T.length;R++)st=T[R],st.processed===!1&&(E.push(st),st.processed=!0);const Tt=[],gt=[];for(R=0;R<E.length;R++)st=E[R],Tt.push(st.bone),gt.push(st.boneInverse);return new Zc(Tt,gt)}function Kt(x,v,T){x.traverse(function(E){if(E.isBone===!0){let R;for(let K=0;K<v.length;K++){const st=v[K];if(st.name===E.name){R=st.boneInverse;break}}R===void 0&&(R=new Yt),T.push({bone:E,boneInverse:R,processed:!1})}})}function ee(x){const v=[],T=x.matrix,E=x.nodes,R=x.type,K=x.instanceCameras,st=x.instanceControllers,Tt=x.instanceLights,gt=x.instanceGeometries,St=x.instanceNodes;for(let ut=0,kt=E.length;ut<kt;ut++)v.push(Be(E[ut]));for(let ut=0,kt=K.length;ut<kt;ut++){const Nt=$t(K[ut]);Nt!==null&&v.push(Nt.clone())}for(let ut=0,kt=st.length;ut<kt;ut++){const Nt=st[ut],Gt=J(Nt.id),Vt=cn(Gt.id),Ue=be(Vt,Nt.materials),Se=Nt.skeletons,ve=Gt.skin.joints,xe=It(Se,ve);for(let Qn=0,hn=Ue.length;Qn<hn;Qn++){const ss=Ue[Qn];ss.isSkinnedMesh&&(ss.bind(xe,Gt.skin.bindMatrix),ss.normalizeSkinWeights()),v.push(ss)}}for(let ut=0,kt=Tt.length;ut<kt;ut++){const Nt=z(Tt[ut]);Nt!==null&&v.push(Nt.clone())}for(let ut=0,kt=gt.length;ut<kt;ut++){const Nt=gt[ut],Gt=cn(Nt.id),Vt=be(Gt,Nt.materials);for(let Ue=0,Se=Vt.length;Ue<Se;Ue++)v.push(Vt[Ue])}for(let ut=0,kt=St.length;ut<kt;ut++)v.push(Be(St[ut]).clone());let Bt;if(E.length===0&&v.length===1)Bt=v[0];else{Bt=R==="JOINT"?new Nu:new ke;for(let ut=0;ut<v.length;ut++)Bt.add(v[ut])}return Bt.name=R==="JOINT"?x.sid:x.name,Bt.matrix.copy(T),Bt.matrix.decompose(Bt.position,Bt.quaternion,Bt.scale),Bt}const Ut=new Ke({name:mi.DEFAULT_MATERIAL_NAME,color:16711935});function pe(x,v){const T=[];for(let E=0,R=x.length;E<R;E++){const K=v[x[E]];K===void 0?(console.warn("THREE.ColladaLoader: Material with key %s not found. Apply fallback material.",x[E]),T.push(Ut)):T.push(Mt(K))}return T}function be(x,v){const T=[];for(const E in x){const R=x[E],K=pe(R.materialKeys,v);if(K.length===0&&(E==="lines"||E==="linestrips"?K.push(new zn):K.push(new Ts)),E==="lines"||E==="linestrips")for(let St=0,Bt=K.length;St<Bt;St++){const ut=K[St];if(ut.isMeshPhongMaterial===!0||ut.isMeshLambertMaterial===!0){const kt=new zn;kt.color.copy(ut.color),kt.opacity=ut.opacity,kt.transparent=ut.transparent,K[St]=kt}}const st=R.data.attributes.skinIndex!==void 0,Tt=K.length===1?K[0]:K;let gt;switch(E){case"lines":gt=new Ta(R.data,Tt);break;case"linestrips":gt=new qs(R.data,Tt);break;case"triangles":case"polylist":st?gt=new H0(R.data,Tt):gt=new ge(R.data,Tt);break}T.push(gt)}return T}function Ee(x){return jt.nodes[x]!==void 0}function Be(x){return _(jt.nodes[x],ee)}function _e(x){const v={name:x.getAttribute("name"),children:[]};$(x);const T=n(x,"node");for(let E=0;E<T.length;E++)v.children.push(yt(T[E]));jt.visualScenes[x.getAttribute("id")]=v}function Ot(x){const v=new ke;v.name=x.name;const T=x.children;for(let E=0;E<T.length;E++){const R=T[E];v.add(Be(R.id))}return v}function Dn(x){return jt.visualScenes[x]!==void 0}function me(x){return _(jt.visualScenes[x],Ot)}function gn(x){const v=n(x,"instance_visual_scene")[0];return me(o(v.getAttribute("url")))}function _i(){const x=jt.clips;if(l(x)===!0){if(l(jt.animations)===!1){const v=[];for(const T in jt.animations){const E=y(T);for(let R=0,K=E.length;R<K;R++)v.push(E[R])}Lr.push(new Lh("default",-1,v))}}else for(const v in x)Lr.push(W(v))}function en(x){let v="";const T=[x];for(;T.length;){const E=T.shift();E.nodeType===Node.TEXT_NODE?v+=E.textContent:(v+=`
`,T.push.apply(T,E.childNodes))}return v.trim()}if(t.length===0)return{scene:new Lu};const vi=new DOMParser().parseFromString(t,"application/xml"),Zt=n(vi,"COLLADA")[0],ln=vi.getElementsByTagName("parsererror")[0];if(ln!==void 0){const x=n(ln,"div")[0];let v;return x?v=x.textContent:v=en(ln),console.error(`THREE.ColladaLoader: Failed to parse collada file.
`,v),null}const Oi=Zt.getAttribute("version");console.debug("THREE.ColladaLoader: File version",Oi);const nn=h(n(Zt,"asset")[0]),In=new Vu(this.manager);In.setPath(this.resourcePath||e).setCrossOrigin(this.crossOrigin);let An;Xh&&(An=new Xh(this.manager),An.setPath(this.resourcePath||e));const ki=new Jt,Lr=[];let dl={},xd=0;const jt={animations:{},clips:{},controllers:{},images:{},effects:{},materials:{},cameras:{},lights:{},geometries:{},nodes:{},visualScenes:{},kinematicsModels:{},physicsModels:{},kinematicsScenes:{}};f(Zt,"library_animations","animation",m),f(Zt,"library_animation_clips","animation_clip",O),f(Zt,"library_controllers","controller",lt),f(Zt,"library_images","image",nt),f(Zt,"library_effects","effect",zt),f(Zt,"library_materials","material",ht),f(Zt,"library_cameras","camera",Ct),f(Zt,"library_lights","light",Lt),f(Zt,"library_geometries","geometry",xt),f(Zt,"library_nodes","node",yt),f(Zt,"library_visual_scenes","visual_scene",_e),f(Zt,"library_kinematics_models","kinematics_model",Nn),f(Zt,"library_physics_models","physics_model",is),f(Zt,"scene","instance_kinematics_scene",Qa),g(jt.animations,w),g(jt.clips,et),g(jt.controllers,wt),g(jt.images,it),g(jt.effects,j),g(jt.materials,Ft),g(jt.cameras,Xt),g(jt.lights,Me),g(jt.geometries,Pe),g(jt.visualScenes,Ot),_i(),V();const Nr=gn(n(Zt,"scene")[0]);return Nr.animations=Lr,nn.upAxis==="Z_UP"&&(console.warn("THREE.ColladaLoader: You are loading an asset with a Z-UP coordinate system. The loader just rotates the asset to transform it into Y-UP. The vertex data are not converted, see #24289."),Nr.rotation.set(-Math.PI/2,0,0)),Nr.scale.multiplyScalar(nn.unit),{get animations(){return console.warn("THREE.ColladaLoader: Please access animations over scene.animations now."),Lr},kinematics:dl,library:jt,scene:Nr}}}const qh=new D,$v=new pn,ha=new Yt,wi=new Yt,ua=new Vn,da=new D(1,1,1),fa=new D;class qa extends De{constructor(...t){super(...t),this.urdfNode=null,this.urdfName=""}copy(t,e){return super.copy(t,e),this.urdfNode=t.urdfNode,this.urdfName=t.urdfName,this}}class Kv extends qa{constructor(...t){super(...t),this.isURDFCollider=!0,this.type="URDFCollider"}}class Jv extends qa{constructor(...t){super(...t),this.isURDFVisual=!0,this.type="URDFVisual"}}class Xu extends qa{constructor(...t){super(...t),this.isURDFLink=!0,this.type="URDFLink",this.inertial={mass:0,origin:{xyz:[0,0,0],rpy:[0,0,0]},inertia:{ixx:0,ixy:0,ixz:0,iyy:0,iyz:0,izz:0}}}copy(t,e){return super.copy(t,e),this.inertial={mass:t.inertial.mass,origin:{xyz:[...t.inertial.origin.xyz],rpy:[...t.inertial.origin.rpy]},inertia:{...t.inertial.inertia}},this}}class qu extends qa{get jointType(){return this._jointType}set jointType(t){if(this.jointType!==t)switch(this._jointType=t,this.matrixWorldNeedsUpdate=!0,t){case"fixed":this.jointValue=[];break;case"continuous":case"revolute":case"prismatic":this.jointValue=new Array(1).fill(0);break;case"planar":this.jointValue=new Array(3).fill(0),this.axis=new D(0,0,1);break;case"floating":this.jointValue=new Array(6).fill(0);break}}get angle(){return this.jointValue[0]}constructor(...t){super(...t),this.isURDFJoint=!0,this.type="URDFJoint",this.jointValue=null,this.jointType="fixed",this.axis=new D(1,0,0),this.limit={lower:0,upper:0,effort:0,velocity:0},this.ignoreLimits=!1,this.origPosition=null,this.origQuaternion=null,this.mimicJoints=[]}copy(t,e){return super.copy(t,e),this.jointType=t.jointType,this.axis=t.axis.clone(),this.limit.lower=t.limit.lower,this.limit.upper=t.limit.upper,this.limit.effort=t.limit.effort,this.limit.velocity=t.limit.velocity,this.ignoreLimits=!1,this.jointValue=[...t.jointValue],this.origPosition=t.origPosition?t.origPosition.clone():null,this.origQuaternion=t.origQuaternion?t.origQuaternion.clone():null,this.mimicJoints=[...t.mimicJoints],this}setJointValue(...t){t=t.map(n=>n===null?null:parseFloat(n)),(!this.origPosition||!this.origQuaternion)&&(this.origPosition=this.position.clone(),this.origQuaternion=this.quaternion.clone());let e=!1;switch(this.mimicJoints.forEach(n=>{e=n.updateFromMimickedJoint(...t)||e}),this.jointType){case"fixed":return e;case"continuous":case"revolute":{let n=t[0];return n==null||n===this.jointValue[0]?e:(!this.ignoreLimits&&this.jointType==="revolute"&&(n=Math.min(this.limit.upper,n),n=Math.max(this.limit.lower,n)),this.quaternion.setFromAxisAngle(this.axis,n).premultiply(this.origQuaternion),this.jointValue[0]!==n?(this.jointValue[0]=n,this.matrixWorldNeedsUpdate=!0,!0):e)}case"prismatic":{let n=t[0];return n==null||n===this.jointValue[0]?e:(this.ignoreLimits||(n=Math.min(this.limit.upper,n),n=Math.max(this.limit.lower,n)),this.position.copy(this.origPosition),qh.copy(this.axis).applyEuler(this.rotation),this.position.addScaledVector(qh,n),this.jointValue[0]!==n?(this.jointValue[0]=n,this.matrixWorldNeedsUpdate=!0,!0):e)}case"floating":return this.jointValue.every((n,s)=>t[s]===n||t[s]===null)?e:(this.jointValue[0]=t[0]!==null?t[0]:this.jointValue[0],this.jointValue[1]=t[1]!==null?t[1]:this.jointValue[1],this.jointValue[2]=t[2]!==null?t[2]:this.jointValue[2],this.jointValue[3]=t[3]!==null?t[3]:this.jointValue[3],this.jointValue[4]=t[4]!==null?t[4]:this.jointValue[4],this.jointValue[5]=t[5]!==null?t[5]:this.jointValue[5],wi.compose(this.origPosition,this.origQuaternion,da),ua.setFromEuler($v.set(this.jointValue[3],this.jointValue[4],this.jointValue[5],"XYZ")),fa.set(this.jointValue[0],this.jointValue[1],this.jointValue[2]),ha.compose(fa,ua,da),wi.premultiply(ha),this.position.setFromMatrixPosition(wi),this.rotation.setFromRotationMatrix(wi),this.matrixWorldNeedsUpdate=!0,!0);case"planar":return this.jointValue.every((n,s)=>t[s]===n||t[s]===null)?e:(this.jointValue[0]=t[0]!==null?t[0]:this.jointValue[0],this.jointValue[1]=t[1]!==null?t[1]:this.jointValue[1],this.jointValue[2]=t[2]!==null?t[2]:this.jointValue[2],wi.compose(this.origPosition,this.origQuaternion,da),ua.setFromAxisAngle(this.axis,this.jointValue[2]),fa.set(this.jointValue[0],this.jointValue[1],0),ha.compose(fa,ua,da),wi.premultiply(ha),this.position.setFromMatrixPosition(wi),this.rotation.setFromRotationMatrix(wi),this.matrixWorldNeedsUpdate=!0,!0)}return e}}class jh extends qu{constructor(...t){super(...t),this.type="URDFMimicJoint",this.mimicJoint=null,this.offset=0,this.multiplier=1}updateFromMimickedJoint(...t){const e=t.map(n=>n===null?null:n*this.multiplier+this.offset);return super.setJointValue(...e)}copy(t,e){return super.copy(t,e),this.mimicJoint=t.mimicJoint,this.offset=t.offset,this.multiplier=t.multiplier,this}}class Zv extends Xu{constructor(...t){super(...t),this.isURDFRobot=!0,this.urdfNode=null,this.urdfRobotNode=null,this.robotName=null,this.links=null,this.joints=null,this.colliders=null,this.visual=null,this.frames=null}copy(t,e){super.copy(t,e),this.urdfRobotNode=t.urdfRobotNode,this.robotName=t.robotName,this.links={},this.joints={},this.colliders={},this.visual={},this.traverse(n=>{n.isURDFJoint&&n.urdfName in t.joints&&(this.joints[n.urdfName]=n),n.isURDFLink&&n.urdfName in t.links&&(this.links[n.urdfName]=n),n.isURDFCollider&&n.urdfName in t.colliders&&(this.colliders[n.urdfName]=n),n.isURDFVisual&&n.urdfName in t.visual&&(this.visual[n.urdfName]=n)});for(const n in this.joints)this.joints[n].mimicJoints=this.joints[n].mimicJoints.map(s=>this.joints[s.name]);return this.frames={...this.colliders,...this.visual,...this.links,...this.joints},this}getFrame(t){return this.frames[t]}setJointValue(t,...e){const n=this.joints[t];return n?n.setJointValue(...e):!1}setJointValues(t){let e=!1;for(const n in t){const s=t[n];Array.isArray(s)?e=this.setJointValue(n,...s)||e:e=this.setJointValue(n,s)||e}return e}}const Xo=new Vn,Yh=new pn;function Ti(i){return i?i.trim().split(/\s+/g).map(t=>parseFloat(t)):[0,0,0]}function $h(i,t,e=!1){e||i.rotation.set(0,0,0),Yh.set(t[0],t[1],t[2],"ZYX"),Xo.setFromEuler(Yh),Xo.multiply(i.quaternion),i.quaternion.copy(Xo)}class Qv{constructor(t){this.manager=t||zu,this.loadMeshCb=this.defaultMeshLoader.bind(this),this.parseVisual=!0,this.parseCollision=!1,this.packages="",this.workingPath="",this.fetchOptions={}}loadAsync(t){return new Promise((e,n)=>{this.load(t,e,null,n)})}load(t,e,n,s){const r=this.manager,a=Gu.extractUrlBase(t),o=this.manager.resolveURL(t);r.itemStart(o),fetch(o,this.fetchOptions).then(c=>{if(c.ok)return n&&n(null),c.text();throw new Error(`URDFLoader: Failed to load url '${o}' with error code ${c.status} : ${c.statusText}.`)}).then(c=>{const l=this.parse(c,this.workingPath||a);e(l),r.itemEnd(o)}).catch(c=>{s?s(c):console.error("URDFLoader: Error loading file.",c),r.itemError(o),r.itemEnd(o)})}parse(t,e=this.workingPath){const n=this.packages,s=this.loadMeshCb,r=this.parseVisual,a=this.parseCollision,o=this.manager,c={},l={},h={};function u(P){if(!/^package:\/\//.test(P))return e?e+P:P;const[w,y]=P.replace(/^package:\/\//,"").split(/\/(.+)/);if(typeof n=="string")return n.endsWith(w)?n+"/"+y:n+"/"+w+"/"+y;if(typeof n=="function")return n(w)+"/"+y;if(typeof n=="object")return w in n?n[w]+"/"+y:(console.error(`URDFLoader : ${w} not found in provided package list.`),null)}function d(P){let w;P instanceof Document?w=[...P.children]:P instanceof Element?w=[P]:w=[...new DOMParser().parseFromString(P,"text/xml").children];const y=w.filter(N=>N.nodeName==="robot").pop();return f(y)}function f(P){const w=[...P.children],y=w.filter(F=>F.nodeName.toLowerCase()==="link"),N=w.filter(F=>F.nodeName.toLowerCase()==="joint"),C=w.filter(F=>F.nodeName.toLowerCase()==="material"),L=new Zv;L.robotName=P.getAttribute("name"),L.urdfRobotNode=P,C.forEach(F=>{const k=F.getAttribute("name");h[k]=m(F)});const I={},M={};y.forEach(F=>{const k=F.getAttribute("name"),H=P.querySelector(`child[link="${k}"]`)===null;c[k]=_(F,I,M,H?L:null)}),N.forEach(F=>{const k=F.getAttribute("name");l[k]=g(F)}),L.joints=l,L.links=c,L.colliders=M,L.visual=I;const b=Object.values(l);return b.forEach(F=>{F instanceof jh&&l[F.mimicJoint].mimicJoints.push(F)}),b.forEach(F=>{const k=new Set,H=Z=>{if(k.has(Z))throw new Error("URDFLoader: Detected an infinite loop of mimic joints.");k.add(Z),Z.mimicJoints.forEach(tt=>{H(tt)})};H(F)}),L.frames={...M,...I,...c,...l},L}function g(P){const w=[...P.children],y=P.getAttribute("type");let N;const C=w.find(k=>k.nodeName.toLowerCase()==="mimic");C?(N=new jh,N.mimicJoint=C.getAttribute("joint"),N.multiplier=parseFloat(C.getAttribute("multiplier")||1),N.offset=parseFloat(C.getAttribute("offset")||0)):N=new qu,N.urdfNode=P,N.name=P.getAttribute("name"),N.urdfName=N.name,N.jointType=y;let L=null,I=null,M=[0,0,0],b=[0,0,0];w.forEach(k=>{const H=k.nodeName.toLowerCase();H==="origin"?(M=Ti(k.getAttribute("xyz")),b=Ti(k.getAttribute("rpy"))):H==="child"?I=c[k.getAttribute("link")]:H==="parent"?L=c[k.getAttribute("link")]:H==="limit"&&(N.limit.lower=parseFloat(k.getAttribute("lower")||N.limit.lower),N.limit.upper=parseFloat(k.getAttribute("upper")||N.limit.upper),N.limit.effort=parseFloat(k.getAttribute("effort")||N.limit.effort),N.limit.velocity=parseFloat(k.getAttribute("velocity")||N.limit.velocity))}),L.add(N),N.add(I),$h(N,b),N.position.set(M[0],M[1],M[2]);const F=w.filter(k=>k.nodeName.toLowerCase()==="axis")[0];if(F){const k=F.getAttribute("xyz").split(/\s+/g).map(H=>parseFloat(H));N.axis=new D(k[0],k[1],k[2]),N.axis.normalize()}return N}function _(P,w,y,N=null){N===null&&(N=new Xu);const C=[...P.children];N.name=P.getAttribute("name"),N.urdfName=N.name,N.urdfNode=P;const L=C.find(I=>I.nodeName.toLowerCase()==="inertial");return L&&[...L.children].forEach(I=>{const M=I.nodeName.toLowerCase();M==="origin"?(N.inertial.origin.xyz=Ti(I.getAttribute("xyz")),N.inertial.origin.rpy=Ti(I.getAttribute("rpy"))):M==="mass"?N.inertial.mass=parseFloat(I.getAttribute("value"))||0:M==="inertia"&&(N.inertial.inertia.ixx=parseFloat(I.getAttribute("ixx"))||0,N.inertial.inertia.ixy=parseFloat(I.getAttribute("ixy"))||0,N.inertial.inertia.ixz=parseFloat(I.getAttribute("ixz"))||0,N.inertial.inertia.iyy=parseFloat(I.getAttribute("iyy"))||0,N.inertial.inertia.iyz=parseFloat(I.getAttribute("iyz"))||0,N.inertial.inertia.izz=parseFloat(I.getAttribute("izz"))||0)}),r&&C.filter(M=>M.nodeName.toLowerCase()==="visual").forEach(M=>{const b=p(M,h);if(N.add(b),M.hasAttribute("name")){const F=M.getAttribute("name");b.name=F,b.urdfName=F,w[F]=b}}),a&&C.filter(M=>M.nodeName.toLowerCase()==="collision").forEach(M=>{const b=p(M);if(N.add(b),M.hasAttribute("name")){const F=M.getAttribute("name");b.name=F,b.urdfName=F,y[F]=b}}),N}function m(P){const w=[...P.children],y=new Ts;return y.name=P.getAttribute("name")||"",w.forEach(N=>{const C=N.nodeName.toLowerCase();if(C==="color"){const L=N.getAttribute("rgba").split(/\s/g).map(I=>parseFloat(I));y.color.setRGB(L[0],L[1],L[2]),y.opacity=L[3],y.transparent=L[3]<1,y.depthWrite=!y.transparent}else if(C==="texture"){const L=N.getAttribute("filename");if(L){const I=new Vu(o),M=u(L);y.map=I.load(M),y.map.colorSpace=Ne}}}),y}function p(P,w={}){const y=P.nodeName.toLowerCase()==="collision",N=[...P.children];let C=null;const L=N.filter(M=>M.nodeName.toLowerCase()==="material")[0];if(L){const M=L.getAttribute("name");M&&M in w?C=w[M]:C=m(L)}else C=new Ts;const I=y?new Kv:new Jv;return I.urdfNode=P,N.forEach(M=>{const b=M.nodeName.toLowerCase();if(b==="geometry"){const F=M.children[0].nodeName.toLowerCase();if(F==="mesh"){const k=M.children[0].getAttribute("filename"),H=u(k);if(H!==null){const Z=M.children[0].getAttribute("scale");if(Z){const tt=Ti(Z);I.scale.set(tt[0],tt[1],tt[2])}s(H,o,(tt,O)=>{O?console.error("URDFLoader: Error loading mesh.",O):tt&&(tt instanceof ge&&(tt.material=C),tt.position.set(0,0,0),tt.quaternion.identity(),I.add(tt))})}}else if(F==="box"){const k=new ge;k.geometry=new Ws(1,1,1),k.material=C;const H=Ti(M.children[0].getAttribute("size"));k.scale.set(H[0],H[1],H[2]),I.add(k)}else if(F==="sphere"){const k=new ge;k.geometry=new pi(1,30,30),k.material=C;const H=parseFloat(M.children[0].getAttribute("radius"))||0;k.scale.set(H,H,H),I.add(k)}else if(F==="cylinder"){const k=new ge;k.geometry=new js(1,1,1,30),k.material=C;const H=parseFloat(M.children[0].getAttribute("radius"))||0,Z=parseFloat(M.children[0].getAttribute("length"))||0;k.scale.set(H,Z,H),k.rotation.set(Math.PI/2,0,0),I.add(k)}}else if(b==="origin"){const F=Ti(M.getAttribute("xyz")),k=Ti(M.getAttribute("rpy"));I.position.set(F[0],F[1],F[2]),I.rotation.set(0,0,0),$h(I,k)}}),I}return d(t)}defaultMeshLoader(t,e,n){/\.stl$/i.test(t)?new jv(e).load(t,r=>{const a=new ge(r,new Ts);n(a)},null,r=>n(null,r)):/\.dae$/i.test(t)?new Yv(e).load(t,r=>n(r.scene),null,r=>n(null,r)):console.warn(`URDFLoader: Could not load model at ${t}.
No loader available`)}}const qo=8,tx=.002;function jo(i,t){return Math.hypot(t.clientX-i.startX,t.clientY-i.startY)}class ex{constructor(t){qt(this,"interaction",null);qt(this,"onPointerDown",t=>{const{canvas:e,layer:n}=this.options,s=this.options.getSession();if(!s||this.options.isBusy()||!t.isPrimary||t.button!==0||s.read_only||s.generation.status==="running")return;const r=this.options.getSelectedHandle(),a=n.pickRestoreGhost(t,r);if(a){this.options.selectHandle(a),this.interaction={kind:"restore",pointerId:t.pointerId,handle:a,startX:t.clientX,startY:t.clientY},this.options.controls.enabled=!1,e.style.cursor="pointer",this.setState("restore-armed"),this.capturePointer(t.pointerId);return}const o=n.pickHandle(t,(s==null?void 0:s.edit_handles)??[],r);if(this.setState(o?"handle-hit":"miss"),!o)return;if((r==null?void 0:r.handle_id)!==o.handle_id){this.options.selectHandle(o),this.setState("selected");return}const c=s==null?void 0:s.surfaces.find(u=>u.surface_id===o.surface_id);if(!c){this.setState("surface-missing");return}const l=new ci().setFromNormalAndCoplanarPoint(new D(...c.normal).normalize(),new D(...c.origin)),h=new D;if(!n.intersectPointerPlane(t,l,h)){this.setState("plane-miss");return}this.interaction={kind:"drag",pointerId:t.pointerId,handle:o,startX:t.clientX,startY:t.clientY,plane:l,offset:new D(...o.world_position).sub(h),preview:null,dragging:!1},this.options.controls.enabled=!1,e.style.cursor="grab",this.setState("armed"),this.capturePointer(t.pointerId)});qt(this,"onPointerMove",t=>{var a,o;const{canvas:e,layer:n}=this.options,s=this.interaction;if(!s){if(this.options.isBusy()||(a=this.options.getSession())!=null&&a.read_only){e.style.cursor="default";return}const c=this.options.getSelectedHandle();e.style.cursor=n.pickRestoreGhost(t,c)?"pointer":n.pickHandle(t,((o=this.options.getSession())==null?void 0:o.edit_handles)??[],c)?"grab":"default";return}if(t.pointerId!==s.pointerId)return;if(s.kind==="restore"){this.setState(jo(s,t)>=qo?"restore-cancelled":"restore-armed");return}if(!s.dragging&&jo(s,t)<qo)return;s.dragging=!0,e.style.cursor="grabbing",this.setState("dragging");const r=new D;n.intersectPointerPlane(t,s.plane,r)&&(s.preview=r.add(s.offset),n.previewPosition(s.handle,s.preview),this.options.updatePositionOffset(s.handle,s.preview),this.setState("preview"))});qt(this,"onPointerUp",async t=>{const e=this.interaction;if(!e||t.pointerId!==e.pointerId)return;if(this.interaction=null,this.options.controls.enabled=!0,this.options.canvas.style.cursor="default",this.releasePointer(t.pointerId),e.kind==="restore"){if(jo(e,t)>=qo){this.setState("restore-cancelled");return}this.setState("restoring"),this.setState(await this.options.restoreHandle(e.handle)?"restored":"error");return}if(!e.dragging||!e.preview){this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.setState("selected");return}const n=e.preview.clone();if(n.distanceTo(new D(...e.handle.world_position))<tx){this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.setState("no-op");return}this.setState("submitting");const s=await this.options.moveHandle(e.handle,n);this.setState(s?"moved":"error"),s||(this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle),this.options.rebuildHandles())});this.options=t;const{canvas:e}=t;e.addEventListener("pointerdown",this.onPointerDown),e.addEventListener("pointermove",this.onPointerMove),e.addEventListener("pointerup",this.onPointerUp),e.addEventListener("pointercancel",()=>this.cancel()),e.addEventListener("pointerleave",()=>{this.interaction&&this.cancel()})}get active(){return this.interaction!==null}cancel(t="cancelled"){const e=this.interaction;(e==null?void 0:e.kind)==="drag"&&(this.options.layer.restorePosition(e.handle),this.options.updatePositionOffset(e.handle)),this.interaction=null,this.options.controls.enabled=!0,this.options.canvas.style.cursor="default",this.setState(t),e&&this.releasePointer(e.pointerId)}setState(t){this.options.canvas.dataset.dragState=t}capturePointer(t){try{this.options.canvas.setPointerCapture(t)}catch{}}releasePointer(t){try{this.options.canvas.hasPointerCapture(t)&&this.options.canvas.releasePointerCapture(t)}catch{}}}function Ai(i){const t=new Set,e=new Set,n=new Set;i.traverse(s=>{const r=s;r.geometry&&!(s.parent instanceof Zi)&&t.add(r.geometry),(Array.isArray(r.material)?r.material:r.material?[r.material]:[]).forEach(o=>e.add(o))}),e.forEach(s=>{Object.values(s).forEach(r=>{r instanceof Je&&n.add(r)}),s.dispose()}),n.forEach(s=>s.dispose()),t.forEach(s=>s.dispose())}function Sn(i){Ai(i),i.clear()}const Kh=.008,nx=.006,Jh=14,ix=10;class sx{constructor(t,e){qt(this,"handles",new ke);qt(this,"restoreGhosts",new ke);qt(this,"handleObjects",new Map);qt(this,"restoreGhostObjects",new Map);qt(this,"handleHitMeshes",[]);qt(this,"restoreGhostHitMeshes",[]);qt(this,"pointer",new At);qt(this,"raycaster",new wv);qt(this,"signature","");this.canvas=t,this.camera=e}clear(){Sn(this.handles),Sn(this.restoreGhosts),this.signature="",this.handleObjects.clear(),this.restoreGhostObjects.clear(),this.handleHitMeshes.length=0,this.restoreGhostHitMeshes.length=0,this.canvas.dataset.restoreGhostCount="0"}setVisible(t){this.handles.visible=t,this.restoreGhosts.visible=t}rebuild({handles:t,visibleHandleIds:e,selectedHandle:n,radius:s}){const r=t.filter(o=>e.has(o.handle_id)||o.handle_id===(n==null?void 0:n.handle_id)),a=JSON.stringify([s,n==null?void 0:n.handle_id,r]);if(a!==this.signature){this.clear(),this.signature=a,this.canvas.dataset.contactMarker="episode-handle";for(const o of t){if(!e.has(o.handle_id)&&o.handle_id!==(n==null?void 0:n.handle_id))continue;const c=o.handle_id===(n==null?void 0:n.handle_id),l=new D(...o.surface_normal).normalize(),h=new D(...o.surface_tangent_u).normalize(),u=new D(...o.surface_tangent_v).normalize(),d=new ke;d.quaternion.setFromRotationMatrix(new Yt().makeBasis(h,u,l)),d.position.set(...o.world_position).addScaledVector(l,Kh);const f=String(o.metadata.surface_editor_status||"bound"),g=c?16768370:f==="edited"?6543004:15134195,_=new ge(new Ca(s*.48,s,32),new Ke({color:g,transparent:!0,opacity:c?1:.82,side:dn,depthTest:!1,depthWrite:!1}));_.renderOrder=8,d.add(_);const m=new ge(new Aa(s*.25,24),new Ke({color:g,side:dn,depthTest:!1,depthWrite:!1}));m.position.z=.001,m.renderOrder=9,d.add(m);const p=new ge(new pi(s*.82,16,10),new Ke({transparent:!0,opacity:0,depthWrite:!1}));p.userData.handle=o,d.add(p),this.handleHitMeshes.push(p),c&&this.addSelectionAxes(d,s),this.handles.add(d),this.handleObjects.set(o.handle_id,d),o.has_position_offset&&this.addRestoreGhost(o,d,l,s)}this.canvas.dataset.restoreGhostCount=String(this.restoreGhostObjects.size)}}pickRestoreGhost(t,e){if(!this.restoreGhosts.visible)return null;this.setPointerRay(t);const n=this.raycaster.intersectObjects(this.restoreGhostHitMeshes,!1)[0];if(n)return n.object.userData.restoreHandle;if(!(e!=null&&e.has_position_offset))return null;const s=this.canvas.getBoundingClientRect(),r=Number(this.canvas.dataset.selectedRestoreGhostX)*s.width,a=Number(this.canvas.dataset.selectedRestoreGhostY)*s.height,o=t.clientX-s.left,c=t.clientY-s.top;return Number.isFinite(r)&&Number.isFinite(a)&&Math.hypot(r-o,a-c)<=ix?e:null}pickHandle(t,e,n){if(!this.handles.visible)return null;this.setPointerRay(t);const s=this.canvas.getBoundingClientRect(),r=t.clientX-s.left,a=t.clientY-s.top,o=this.raycaster.intersectObjects(this.handleHitMeshes,!1),c=o.find(u=>u.object.userData.handle.handle_id===(n==null?void 0:n.handle_id));if(c)return c.object.userData.handle;if(n){const u=Number(this.canvas.dataset.selectedHandleX)*s.width,d=Number(this.canvas.dataset.selectedHandleY)*s.height;if(Number.isFinite(u)&&Number.isFinite(d)&&Math.hypot(u-r,d-a)<=Jh)return n}if(o[0])return o[0].object.userData.handle;let l=null,h=Jh;for(const u of e){const d=this.handleObjects.get(u.handle_id);if(!d)continue;const f=d.getWorldPosition(new D).project(this.camera);if(f.z<-1||f.z>1)continue;const g=(f.x+1)*.5*s.width,_=(1-f.y)*.5*s.height,m=Math.hypot(g-r,_-a);m<=h&&(l=u,h=m)}return l}intersectPointerPlane(t,e,n){return this.setPointerRay(t),this.raycaster.ray.intersectPlane(e,n)!==null}previewPosition(t,e){const n=this.handleObjects.get(t.handle_id);n&&n.position.copy(e).addScaledVector(new D(...t.surface_normal),Kh)}restorePosition(t){this.previewPosition(t,new D(...t.world_position))}updateProjection(t){const e=t?this.handleObjects.get(t.handle_id):null,n=t?this.restoreGhostObjects.get(t.handle_id):null;if(n){const r=n.getWorldPosition(new D).project(this.camera);this.canvas.dataset.selectedRestoreGhostX=String((r.x+1)/2),this.canvas.dataset.selectedRestoreGhostY=String((1-r.y)/2)}else delete this.canvas.dataset.selectedRestoreGhostX,delete this.canvas.dataset.selectedRestoreGhostY;if(!e){delete this.canvas.dataset.selectedHandleX,delete this.canvas.dataset.selectedHandleY,delete this.canvas.dataset.selectedHandleId;return}const s=e.getWorldPosition(new D).project(this.camera);this.canvas.dataset.selectedHandleX=String((s.x+1)/2),this.canvas.dataset.selectedHandleY=String((1-s.y)/2),this.canvas.dataset.selectedHandleId=t.handle_id}setPointerRay(t){const e=this.canvas.getBoundingClientRect();this.pointer.x=(t.clientX-e.left)/e.width*2-1,this.pointer.y=-((t.clientY-e.top)/e.height)*2+1,this.raycaster.setFromCamera(this.pointer,this.camera)}addSelectionAxes(t,e){const n=e*1.85,s=new Zi(new D(1,0,0),new D,n,15754313,e*.42,e*.22),r=new Zi(new D(0,1,0),new D,n,6869905,e*.42,e*.22);for(const a of[s.line,s.cone,r.line,r.cone])(Array.isArray(a.material)?a.material:[a.material]).forEach(c=>{c.depthTest=!1,c.depthWrite=!1});t.add(s,r)}addRestoreGhost(t,e,n,s){const r=new ke;r.quaternion.copy(e.quaternion),r.position.set(...t.initial_world_position).addScaledVector(n,nx);const a={color:10136505,transparent:!0,side:dn,depthTest:!1,depthWrite:!1},o=new ge(new Ca(s*.5,s*.92,32),new Ke({...a,opacity:.24}));o.renderOrder=7,r.add(o);const c=new ge(new Aa(s*.16,20),new Ke({...a,opacity:.2}));c.position.z=.001,c.renderOrder=7,r.add(c);const l=new ge(new pi(s*.78,14,8),new Ke({transparent:!0,opacity:0,depthWrite:!1}));l.userData.restoreHandle=t,r.add(l),this.restoreGhostHitMeshes.push(l),this.restoreGhosts.add(r),this.restoreGhostObjects.set(t.handle_id,r)}}const rx=1e-6;function ax(i,t){const e=((t==null?void 0:t.clone())??new D(...i.world_position)).sub(new D(...i.initial_world_position));return{u:e.dot(new D(...i.surface_tangent_u)),v:e.dot(new D(...i.surface_tangent_v))}}function Zh(i){const t=Math.abs(i)<5e-7?0:i;return`${t>=0?"+":""}${t.toFixed(3)} m`}class ju extends Error{constructor(t,e){super(e),this.status=t}}async function Ln(i,t){const e=await fetch(i,{headers:{"Content-Type":"application/json"},...t});if(!e.ok){const n=await e.json().catch(()=>({})),s=Array.isArray(n.detail)?n.detail.map(r=>{var a;return`${((a=r.loc)==null?void 0:a.join("."))||"Request"}: ${r.msg||"Invalid value"}`}).join(`
`):typeof n.detail=="string"?n.detail:e.statusText;throw new ju(e.status,s||`HTTP ${e.status}`)}return e.json()}const ox={left_foot:["LHEE","LTOE"],right_foot:["RHEE","RTOE"],left_hand:["LH"],right_hand:["RH"],left_knee:["LK"],right_knee:["RK"]},Qh=new WeakMap;function cx(i){const t=Qh.get(i);if(t)return t;const e=i.contact_force.part_order.map((n,s)=>{var o;const r=[];let a=-1;for(let c=0;c<=i.qpos.length;c++){const l=c<i.qpos.length&&!!((o=i.contact_force.masks[c])!=null&&o[s]);l&&a<0&&(a=c),!l&&a>=0&&(r.push([a,c]),a=-1)}return r});return Qh.set(i,e),e}function Yu(i,t=8){const e=i.getBoundingClientRect(),n=Math.max(1,t),s=e.width<560?54:68,r=28;return{width:e.width,height:e.height,labelW:s,rulerH:r,rowH:Math.max(1,(e.height-r)/n),plotW:Math.max(1,e.width-s),rows:n}}function ai(i,t,e){return t.labelW+i/Math.max(1,e-1)*t.plotW}function lx(i,t,e){const n=Math.max(0,Math.min(1,(i-t.labelW)/t.plotW));return Math.round(n*Math.max(0,e-1))}function hx(i){const t=10**Math.floor(Math.log10(Math.max(i,1e-6))),e=i/t;return(e<=1?1:e<=2?2:e<=5?5:10)*t}function $u(i){const t=Math.floor(i/60),e=i-t*60;return t?`${t}:${e.toFixed(e<10?1:0).padStart(e<10?4:2,"0")}`:`${e.toFixed(e<10?1:0)}s`}function ux(i){var y;const{canvas:t,session:e,frame:n,selectedHandle:s,stableCuts:r,partColors:a}=i,o=Yu(t,(e==null?void 0:e.contact_force.part_order.length)??8),c=t.getContext("2d");if(!c)return;const l=Math.min(window.devicePixelRatio,2),h=Math.max(1,Math.round(o.width*l)),u=Math.max(1,Math.round(o.height*l));if(t.width!==h&&(t.width=h),t.height!==u&&(t.height=u),c.setTransform(l,0,0,l,0,0),c.clearRect(0,0,o.width,o.height),c.fillStyle="#0b1117",c.fillRect(0,0,o.width,o.height),!e)return;const d=e.qpos.length;c.fillStyle="#0d141b",c.fillRect(0,0,o.labelW,o.height),c.fillStyle="#111923",c.fillRect(o.labelW,0,o.plotW,o.rulerH);for(let N=0;N<o.rows;N++){const C=o.rulerH+N*o.rowH;c.fillStyle=N%2===0?"#121a22":"#0f171f",c.fillRect(o.labelW,C,o.plotW,o.rowH),c.strokeStyle="#22303c",c.beginPath(),c.moveTo(0,Math.round(C)+.5),c.lineTo(o.width,Math.round(C)+.5),c.stroke(),c.fillStyle=`#${a[N%a.length].toString(16).padStart(6,"0")}`,c.fillRect(8,C+o.rowH/2-3,6,6),c.fillStyle="#aebbc7",c.font="600 10px ui-monospace,monospace",c.textBaseline="middle",c.fillText(e.contact_force.part_order[N]||"",20,C+o.rowH/2)}const f=Math.max(1,d-1)/e.fps,g=hx(f/Math.max(2,Math.floor(o.plotW/92))),_=Math.max(1,Math.round(g*e.fps)),m=Math.max(1,Math.round(_/5)),p=new Set;for(let N=0;N<d;N+=m)p.add(N);for(let N=0;N<d;N+=_)p.add(N);for(const N of[...p].sort((C,L)=>C-L)){const C=Math.round(ai(N,o,d))+.5,L=N%_===0;c.strokeStyle=L?"#344451":"#1d2a34",c.globalAlpha=L?.9:.65,c.beginPath(),c.moveTo(C,L?o.rulerH-7:o.rulerH-4),c.lineTo(C,o.height),c.stroke(),c.globalAlpha=1,L&&(c.fillStyle="#aeb5bd",c.font="10px ui-monospace,monospace",c.fillText($u(N/e.fps),Math.min(C+4,o.width-38),10),c.fillStyle="#6f7780",c.font="9px ui-monospace,monospace",c.fillText(String(N),Math.min(C+4,o.width-32),21))}c.fillStyle="#7e8790",c.font="9px ui-monospace,monospace",c.fillText("TIME",8,9),c.fillText("FRAME",8,21);const P=cx(e);for(let N=0;N<P.length;N++)for(const[C,L]of P[N]){const I=ai(C,o,d),M=ai(Math.max(C,L-1),o,d)+Math.max(1,o.plotW/d);c.fillStyle=`#${a[N%a.length].toString(16).padStart(6,"0")}`,c.globalAlpha=.78,c.beginPath(),c.roundRect(I,o.rulerH+N*o.rowH+3,Math.max(2,M-I),Math.max(2,o.rowH-6),2),c.fill(),c.globalAlpha=1}if(!e.contact_force.part_order.length||e.contact_force.mask_status&&e.contact_force.mask_status!=="verified_newton_primary_faces"){c.fillStyle="#8c9aaa",c.font="12px sans-serif",c.fillText("接触状态未知 · 时间轴用于回放定位",o.labelW+12,o.rulerH+24);for(const N of((y=e.review)==null?void 0:y.segments)??[]){const C=ai(N.start,o,d),L=ai(N.end,o,d);c.fillStyle="#27505e",c.fillRect(C,o.rulerH+42,Math.max(2,L-C),18),L-C>36&&(c.fillStyle="#dce7ed",c.fillText(N.label,C+3,o.rulerH+55))}}if(s){const N=e.contact_force.part_order.includes(s.body)?[s.body]:ox[s.body]||[s.body],C=ai(s.start_frame,o,d),L=ai(Math.max(s.start_frame,s.end_frame-1),o,d);for(const I of N){const M=e.contact_force.part_order.indexOf(I);M<0||(c.strokeStyle="#b7fff1",c.lineWidth=1.5,c.strokeRect(C+.5,o.rulerH+M*o.rowH+2.5,Math.max(3,L-C),Math.max(3,o.rowH-5)),c.lineWidth=1)}}c.setLineDash([3,3]);for(const N of r){const C=Math.round(ai(N,o,d))+.5;c.strokeStyle="#d9b96e",c.globalAlpha=.38,c.beginPath(),c.moveTo(C,o.rulerH),c.lineTo(C,o.height),c.stroke()}c.setLineDash([]),c.globalAlpha=1;const w=Math.round(ai(n,o,d))+.5;c.strokeStyle="#72ead3",c.lineWidth=1.5,c.beginPath(),c.moveTo(w,0),c.lineTo(w,o.height),c.stroke(),c.fillStyle="#72ead3",c.beginPath(),c.moveTo(w-5,0),c.lineTo(w+5,0),c.lineTo(w,7),c.closePath(),c.fill(),c.lineWidth=1}/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ku=(i,t,e=[])=>{const n=document.createElementNS("http://www.w3.org/2000/svg",i);return Object.keys(t).forEach(s=>{n.setAttribute(s,String(t[s]))}),e.length&&e.forEach(s=>{const r=Ku(...s);n.appendChild(r)}),n};var dx=([i,t,e])=>Ku(i,t,e);/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const fx=i=>Array.from(i.attributes).reduce((t,e)=>(t[e.name]=e.value,t),{}),px=i=>typeof i=="string"?i:!i||!i.class?"":i.class&&typeof i.class=="string"?i.class.split(" "):i.class&&Array.isArray(i.class)?i.class:"",mx=i=>i.flatMap(px).map(e=>e.trim()).filter(Boolean).filter((e,n,s)=>s.indexOf(e)===n).join(" "),gx=i=>i.replace(/(\w)(\w*)(_|-|\s*)/g,(t,e,n)=>e.toUpperCase()+n.toLowerCase()),tu=(i,{nameAttr:t,icons:e,attrs:n})=>{var g;const s=i.getAttribute(t);if(s==null)return;const r=gx(s),a=e[r];if(!a)return console.warn(`${i.outerHTML} icon name was not found in the provided icons object.`);const o=fx(i),[c,l,h]=a,u={...l,"data-lucide":s,...n,...o},d=mx(["lucide",`lucide-${s}`,o,n]);d&&Object.assign(u,{class:d});const f=dx([c,u,h]);return(g=i.parentNode)==null?void 0:g.replaceChild(f,i)};/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Fe={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"};/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const _x=["svg",Fe,[["path",{d:"M12 5v14"}],["path",{d:"m19 12-7 7-7-7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const vx=["svg",Fe,[["path",{d:"m12 19-7-7 7-7"}],["path",{d:"M19 12H5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const xx=["svg",Fe,[["path",{d:"M5 12h14"}],["path",{d:"m12 5 7 7-7 7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const yx=["svg",Fe,[["path",{d:"m5 12 7-7 7 7"}],["path",{d:"M12 19V5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Mx=["svg",Fe,[["path",{d:"M20 6 9 17l-5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const bx=["svg",Fe,[["path",{d:"m15 18-6-6 6-6"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Sx=["svg",Fe,[["path",{d:"m9 18 6-6-6-6"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ex=["svg",Fe,[["path",{d:"m11 17-5-5 5-5"}],["path",{d:"m18 17-5-5 5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const wx=["svg",Fe,[["path",{d:"m6 17 5-5-5-5"}],["path",{d:"m13 17 5-5-5-5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Tx=["svg",Fe,[["circle",{cx:"12",cy:"12",r:"3"}],["path",{d:"M3 7V5a2 2 0 0 1 2-2h2"}],["path",{d:"M17 3h2a2 2 0 0 1 2 2v2"}],["path",{d:"M21 17v2a2 2 0 0 1-2 2h-2"}],["path",{d:"M7 21H5a2 2 0 0 1-2-2v-2"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ax=["svg",Fe,[["path",{d:"m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Cx=["svg",Fe,[["path",{d:"M21 12a9 9 0 1 1-6.219-8.56"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Rx=["svg",Fe,[["rect",{x:"14",y:"4",width:"4",height:"16",rx:"1"}],["rect",{x:"6",y:"4",width:"4",height:"16",rx:"1"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Px=["svg",Fe,[["polygon",{points:"6 3 20 12 6 21 6 3"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Lx=["svg",Fe,[["path",{d:"m15 14 5-5-5-5"}],["path",{d:"M20 9H9.5A5.5 5.5 0 0 0 4 14.5A5.5 5.5 0 0 0 9.5 20H13"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Nx=["svg",Fe,[["path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"}],["path",{d:"M21 3v5h-5"}],["path",{d:"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"}],["path",{d:"M8 16H3v5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Dx=["svg",Fe,[["path",{d:"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"}],["path",{d:"M3 3v5h5"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ix=["svg",Fe,[["path",{d:"M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"}],["path",{d:"M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"}],["path",{d:"M7 3v4a1 1 0 0 0 1 1h7"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ux=["svg",Fe,[["line",{x1:"18",x2:"18",y1:"20",y2:"4"}],["polygon",{points:"14,20 4,12 14,4"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Fx=["svg",Fe,[["line",{x1:"6",x2:"6",y1:"4",y2:"20"}],["polygon",{points:"10,4 20,12 10,20"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Ox=["svg",Fe,[["path",{d:"M3 6h18"}],["path",{d:"M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"}],["path",{d:"M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"}],["line",{x1:"10",x2:"10",y1:"11",y2:"17"}],["line",{x1:"14",x2:"14",y1:"11",y2:"17"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const kx=["svg",Fe,[["path",{d:"M9 14 4 9l5-5"}],["path",{d:"M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Bx=["svg",Fe,[["path",{d:"m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"}],["path",{d:"m14 7 3 3"}],["path",{d:"M5 6v4"}],["path",{d:"M19 14v4"}],["path",{d:"M10 2v2"}],["path",{d:"M7 8H3"}],["path",{d:"M21 16h-4"}],["path",{d:"M11 3H9"}]]];/**
 * @license lucide v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const zx=({icons:i={},nameAttr:t="data-lucide",attrs:e={}}={})=>{if(!Object.values(i).length)throw new Error(`Please provide an icons object.
If you want to use all the icons you can import it like:
 \`import { createIcons, icons } from 'lucide';
lucide.createIcons({icons});\``);if(typeof document>"u")throw new Error("`createIcons()` only works in a browser environment.");const n=document.querySelectorAll(`[${t}]`);if(Array.from(n).forEach(s=>tu(s,{nameAttr:t,icons:i,attrs:e})),t==="data-lucide"){const s=document.querySelectorAll("[icon-name]");s.length>0&&(console.warn("[Lucide] Some icons were found with the now deprecated icon-name attribute. These will still be replaced for backwards compatibility, but will no longer be supported in v1.0 and you should switch to data-lucide"),Array.from(s).forEach(r=>tu(r,{nameAttr:"icon-name",icons:i,attrs:e})))}},Vx=()=>`
  <header class="topbar">
    <div class="brand"><div><strong>Motion Edit</strong><span id="motionLabel">No motion</span></div></div>
    <div class="top-actions">
      <button class="icon" id="openMotionBtn" title="Open registered motion" aria-label="Open registered motion"><i data-lucide="folder-open"></i></button>
      <button class="icon" id="focusBtn" title="Frame scene"><i data-lucide="focus"></i></button>
      <button class="icon" id="undoBtn" title="Undo"><i data-lucide="undo-2"></i></button>
      <button class="icon" id="redoBtn" title="Redo"><i data-lucide="redo-2"></i></button>
      <button class="icon primary" id="saveBtn" title="Save contact edit plan"><i data-lucide="save"></i></button>
    </div>
  </header>`,Hx=()=>`
  <section class="viewport">
    <canvas id="scene"></canvas>
    <div class="viewport-hud"><strong id="viewportMotion">No motion loaded</strong><span id="viewportFrame">Frame 0</span><span id="viewportTime">0.00 s</span></div>
    <div class="shortcut-hint"><span>Space</span> Play <span>← →</span> Frame <span>[ ]</span> Contact</div>
    <div id="sceneStatus" class="scene-status">Select a motion asset</div>
    <button id="retryLoad" class="retry-load" hidden>Retry loading</button>
  </section>`,Gx=()=>`
  <div class="tab-page active" data-page="contact">
    <div class="page-heading"><strong>Contacts</strong><div class="heading-stats"><span id="anchorCount">0 handles</span><span id="editCount">0 edits</span></div></div>
    <section id="collectionPanel" hidden>
      <label class="stack-field"><span>案例</span><select id="reviewCase" aria-label="案例"></select></label>
      <label class="stack-field"><span>参考轨迹</span><select id="reviewReference" aria-label="参考轨迹"></select></label>
      <label class="stack-field"><span>对比方式</span><select id="reviewLayout" aria-label="对比方式"><option value="beside">并排：参考在 −Y，当前在 +Y</option><option value="overlay">原坐标叠加：蓝色为参考</option></select></label>
      <p id="comparisonClock"></p>
      <label class="stack-field"><span>片段</span><select id="reviewSegment" aria-label="片段"></select></label>
      <p id="reviewMetrics"></p><button id="reviewWorst">定位最大穿透帧</button>
    </section>
    <section id="reviewPanel" hidden></section>
    <p id="playbackNotice" class="playback-notice" hidden>只读轨迹：接触状态以已验证的 Newton 数据为准；无接触层时不显示编辑手柄。</p>
    <div id="selection" class="selection empty">None</div>
    <div class="position-offset disabled" id="positionOffset">
      <div class="panel-title">Position offset</div>
      <dl><div><dt>Δu</dt><dd id="offsetU">—</dd></div><div><dt>Δv</dt><dd id="offsetV">—</dd></div></dl>
    </div>
    <div class="anchor-browser">
      <div class="browser-heading">Browse contact episodes</div>
      <div class="anchor-nav"><button class="nav-command" id="prevAnchor" title="Previous matching episode across the trajectory (wraps at start)"><i data-lucide="chevron-left"></i><span>Previous</span></button><button class="nav-command" id="nextAnchor" title="Next matching episode across the trajectory (wraps at end)"><span>Next</span><i data-lucide="chevron-right"></i></button></div>
      <div id="episodeBrowseStatus" class="episode-browse-status" role="status" aria-live="polite">No matching episodes</div>
      <div class="filter-grid"><input id="anchorSearch" aria-label="Filter contact episodes" placeholder="Filter body, surface, id" /><select id="statusFilter" aria-label="Contact episode status"><option value="all">All status</option><option value="bound">Bound</option><option value="edited">Edited</option></select></div>
      <div class="browse-options"><label class="toggle"><input id="currentOnly" type="checkbox" checked /><span>Current frame only</span></label><label class="field" title="How dragging handles beyond the bound surface is handled"><span>Boundary</span><select id="modeSelect" aria-label="Drag boundary behavior"><option value="reject">Reject</option><option value="clamp">Clamp</option></select></label></div>
      <p class="episode-browse-help">Current frame only controls 3D visibility. Previous / Next browse all matching episodes. Boundary applies to dragging.</p>
    </div>
  </div>`,Wx=()=>`
  <div class="tab-page" data-page="display">
    <div class="page-heading"><strong>Display</strong></div>
    <section class="display-section"><div class="section-heading">Scene</div><div class="layer-list">
      <label class="toggle"><input id="terrainToggle" type="checkbox" checked /><span>Terrain mesh</span></label><label class="toggle"><input id="surfaceToggle" type="checkbox" /><span>Contact surfaces</span></label><label class="toggle"><input id="contactSampleToggle" type="checkbox" checked /><span>Contact point + force</span></label><label class="toggle"><input id="handleToggle" type="checkbox" checked /><span>Edit handles</span></label><label class="toggle"><input id="rootPathToggle" type="checkbox" /><span>Root path</span></label><label class="toggle"><input id="guideToggle" type="checkbox" checked /><span>Selection guides</span></label>
    </div></section>
    <section class="display-section"><div class="section-heading">Appearance</div><label class="slider-field"><span>Handle size</span><input id="handleSize" type="range" min="70" max="180" value="110" /></label><label class="slider-field"><span>Force scale</span><input id="forceScale" type="range" min="25" max="300" value="100" /></label></section>
    <section class="display-section"><div class="section-heading">Camera / Terrain</div>
      <button id="focusRobot">聚焦机器人</button>
      <label class="toggle"><input id="followRobot" type="checkbox" /><span>跟随当前机器人</span></label>
      <label class="slider-field"><span>地形透明度</span><input id="terrainOpacity" aria-label="地形透明度" type="range" min="0.05" max="1" step="0.05" value="1" /></label>
    </section>
    <section class="display-section"><div class="section-heading">Channels</div><div id="partLegend" class="part-legend"></div></section>
  </div>`,Xx=()=>`
  <div class="tab-page" data-page="output">
    <div class="page-heading"><strong>Output</strong></div>
    <div id="generationStatus" class="generation-status idle"><strong>Ready</strong><span>Candidate · native validation required</span></div>
    <div id="planStatus" class="plan-status">No plan saved</div>
    <div class="pipeline-actions"><button id="validateBtn" class="secondary-command"><i data-lucide="check"></i><span>Validate</span></button><button id="generateBtn" class="generate-command"><i data-lucide="wand-sparkles"></i><span>Generate</span></button></div>
    <details class="output-settings"><summary>Advanced settings</summary><label class="stack-field"><span>Edit plan</span><input id="planPath" /></label><label class="stack-field"><span>Generated motion</span><input id="outputMotion" /></label><label class="stack-field"><span>Edited contact draft</span><input id="outputLayer" /></label><label class="stack-field"><span>Motion ID</span><input id="outputMotionId" /></label><label class="toggle"><input id="registerMotion" type="checkbox" checked /><span>Register motion</span></label><label class="toggle"><input id="overwriteOutput" type="checkbox" /><span>Replace existing output</span></label></details>
    <div class="source-reference"><span>Source contact layer</span><code id="sourceLayer"></code></div>
    <div class="session-actions"><button id="reloadBtn"><i data-lucide="refresh-cw"></i><span>Reload</span></button><button id="discardBtn"><i data-lucide="trash-2"></i><span>Discard edits</span></button></div>
  </div>`,qx=()=>`
  <aside class="inspector">
    <div class="inspector-tabs"><button data-tab="contact" class="active">Contact</button><button data-tab="display">Display</button><button data-tab="output">Output</button></div>
    <div class="inspector-pages">${Gx()}${Wx()}${Xx()}</div>
    <section class="recent-motion-dock" aria-label="Motions opened this session"><div class="recent-motion-head"><span>This session</span><small id="recentMotionCount">0</small></div><div id="recentMotionList" class="recent-motion-list"></div><details><summary>打开只读回放／实验报告</summary><input id="reviewPath" aria-label="回放或案例清单路径" placeholder="NPZ / 报告 / manifest.json / cases.json" /><input id="reviewTerrain" aria-label="地形路径" placeholder="地形 OBJ 路径（可选）" /><button id="reviewOpen">打开</button></details></section>
  </aside>`,jx=()=>`
  <section class="timeline-panel">
    <div id="timelineResizer" class="timeline-resizer" title="Drag to resize timeline"><span></span></div>
    <div class="transport"><div class="toolbar-group cut-nav"><button class="icon" id="prevCut" title="Previous stable cut"><i data-lucide="chevrons-left"></i></button><button class="icon" id="nextCut" title="Next stable cut"><i data-lucide="chevrons-right"></i></button></div><div class="transport-main"><div class="toolbar-group playback-nav"><button class="icon" id="prevBtn" title="Previous frame"><i data-lucide="step-back"></i></button><button class="icon play" id="playBtn" title="Play or pause"><i data-lucide="play"></i></button><button class="icon" id="nextBtn" title="Next frame"><i data-lucide="step-forward"></i></button></div><div class="frame-readout"><input id="frameInput" class="frame-input" type="number" min="0" value="0" /><span id="frameTotal">/ 0</span></div></div><label class="fps">FPS <input id="fpsInput" type="number" min="1" max="240" value="50" /></label></div>
    <div class="timeline-wrap"><canvas id="timeline" aria-label="Contact timeline"></canvas><div id="timelineHover" class="timeline-hover hidden"></div></div>
  </section>`;function Yx(i){const t=document.createElement("template");t.innerHTML=`${Vx()}<main class="workspace">${Hx()}${qx()}${jx()}</main>
    <dialog id="motionPicker" aria-labelledby="motionPickerTitle"><div class="motion-picker-head"><strong id="motionPickerTitle">打开已注册轨迹</strong><button id="closeMotionPicker" aria-label="Close motion picker">关闭</button></div><label for="motionSearch">搜索名称或 ID</label><input id="motionSearch" type="search" autocomplete="off" placeholder="搜索轨迹" /><div id="motionPickerList"></div></dialog>`,i.replaceChildren(t.content.cloneNode(!0)),sl()}function sl(){zx({icons:{Play:Px,Pause:Rx,StepBack:Ux,StepForward:Fx,Undo2:kx,Redo2:Lx,Save:Ix,RotateCcw:Dx,Focus:Tx,FolderOpen:Ax,RefreshCw:Nx,Check:Mx,ChevronLeft:bx,ChevronRight:Sx,ChevronsLeft:Ex,ChevronsRight:wx,ArrowLeft:vx,ArrowRight:xx,ArrowUp:yx,ArrowDown:_x,Trash2:Ox,WandSparkles:Bx,LoaderCircle:Cx}})}function X(i){const t=document.getElementById(i);if(!t)throw new Error(`missing UI element #${i}`);return t}function $x(){const i=[...document.querySelectorAll("[data-tab]")],t=[...document.querySelectorAll("[data-page]")];for(const e of i)e.addEventListener("click",()=>{const n=e.dataset.tab;for(const s of i)s.classList.toggle("active",s===e);for(const s of t)s.classList.toggle("active",s.dataset.page===n)})}class Kx{constructor(t,e){qt(this,"group",new ke);qt(this,"annotations",new ke);qt(this,"reference",null);qt(this,"current",null);qt(this,"review");qt(this,"selected");qt(this,"spacing",1);qt(this,"link","left_ankle_roll_link");qt(this,"normals",!0);qt(this,"displacement",!0);qt(this,"scale",3);qt(this,"panel");qt(this,"details");this.scene=t,this.onPose=e,this.panel=document.getElementById("reviewPanel"),this.details=document.createElement("pre"),this.details.style.whiteSpace="pre-wrap",this.scene.add(this.group,this.annotations)}clearAnnotations(){Sn(this.annotations)}setup(t,e,n,s){var P,w;if(this.group.clear(),this.clearAnnotations(),this.panel.replaceChildren(),this.review=t,this.current=e,this.reference=null,this.selected=void 0,this.panel.hidden=!t,!t||t.kind==="support_motion"||t.kind==="support_slip")return;const r=document.createElement("p");if(r.textContent=t.notice,this.panel.append(r),t.kind!=="report"||!((P=t.records)!=null&&P.length))return;const a=t.records,o=a.find(y=>y.label===t.reference)||a[0];this.reference=e.clone(),this.spacing=n?Math.max(1,new Gn().setFromObject(n).getSize(new D).y/2+.5):1;const c=o.q;if(this.reference.position.set(c[0],c[1]-this.spacing,c[2]),this.reference.quaternion.set(c[4],c[5],c[6],c[3]),s.forEach((y,N)=>this.reference.setJointValue(y,c[7+N])),this.group.add(this.reference),n){const y=n.clone();y.position.y-=this.spacing,this.group.add(y),n.position.y+=this.spacing}const l=document.createElement("p");l.textContent="左：原始姿态　右：选中结果",this.panel.append(l);const h=document.createElement("select"),u=document.createElement("select");h.setAttribute("aria-label","实验方法"),h.id="reviewMethod",u.setAttribute("aria-label","保存的迭代"),u.id="reviewIteration",[...new Set(a.map(y=>y.method))].forEach(y=>h.add(new Option(y,y)));const d=()=>{this.selected=a.find(y=>y.label===u.value),this.onPose(this.selected.q)},f=()=>{u.replaceChildren();const y=a.filter(C=>C.method===h.value),N=C=>C.iteration==="initial"?-1:C.iteration==="final"?1/0:Number(C.iteration.replace("step",""))||0;y.sort((C,L)=>N(C)-N(L)),y.forEach(C=>u.add(new Option(C.iteration,C.label))),u.value=(y.find(C=>C.iteration==="final")||y[0]).label,d()};h.onchange=f,u.onchange=d;const g=(y,N)=>{const C=document.createElement("label");C.className="stack-field";const L=document.createElement("span");L.textContent=y,C.append(L,N),this.panel.append(C)};g("实验方法",h),g("保存的迭代",u);const _=document.createElement("select");_.id="reviewLink",_.setAttribute("aria-label","位移部位"),Object.keys(e.links).forEach(y=>_.add(new Option(y,y))),_.value=e.links[this.link]?this.link:Object.keys(e.links)[0],this.link=_.value,_.onchange=()=>{this.link=_.value,this.onPose(this.selected.q)},g("位移部位",_);const m=(y,N,C)=>{const L=document.createElement("label");L.className="toggle";const I=document.createElement("input");I.type="checkbox",I.checked=N,I.onchange=()=>{C(I.checked),this.onPose(this.selected.q)},L.append(I,document.createTextNode(y)),this.panel.append(L)};m("穿透法线（报告记录）",this.normals,y=>this.normals=y),m("材料点实际位移 dx",this.displacement,y=>this.displacement=y);const p=document.createElement("input");p.type="range",p.min="1",p.max="20",p.value=String(this.scale),p.setAttribute("aria-label","位移显示倍率"),p.oninput=()=>{this.scale=Number(p.value),this.onPose(this.selected.q)},g("位移显示倍率",p),this.panel.append(this.details),h.value=((w=a.find(y=>y.label!==o.label))==null?void 0:w.method)||o.method,f()}update(){var l;if(!this.reference||!this.current||!this.selected||!((l=this.review)!=null&&l.records))return;this.current.position.y+=this.spacing,this.current.updateMatrixWorld(!0),this.reference.updateMatrixWorld(!0),this.clearAnnotations();const t=this.review.records.find(h=>h.label===this.review.reference)||this.review.records[0];[t,this.selected].forEach((h,u)=>{const d=u===0?-this.spacing:this.spacing;this.normals&&h.normal_starts.forEach((_,m)=>{const p=new D(...h.normals[m]);p.length()>0&&this.annotations.add(new Zi(p.normalize(),new D(_[0],_[1]+d,_[2]),.08,16733525,.015,.008))});const f=h.diagnostics.contact_position_w,g=h.diagnostics.actual_contact;f==null||f.forEach((_,m)=>{if(!(g!=null&&g[m])||!_.every(Number.isFinite))return;const p=new ge(new pi(.012,8,6),new Ke({color:11184810}));p.position.set(_[0],_[1]+d,_[2]),this.annotations.add(p)})});const e=this.reference.links[this.link],n=this.current.links[this.link],s=[],r=[];e==null||e.traverse(h=>{h.isMesh&&s.push(h)}),n==null||n.traverse(h=>{h.isMesh&&r.push(h)});const a=new D;let o=0;s.forEach((h,u)=>{const d=h.geometry.getAttribute("position"),f=r[u];if(!(!d||!f))for(let g=0;g<d.count;g+=Math.max(1,Math.ceil(d.count/12))){const _=new D().fromBufferAttribute(d,g).applyMatrix4(h.matrixWorld);_.y+=2*this.spacing;const p=new D().fromBufferAttribute(d,g).applyMatrix4(f.matrixWorld).sub(_);a.add(p),o++;const P=p.length();this.displacement&&P>1e-8&&this.annotations.add(new Zi(p.normalize(),_,P*this.scale,4255632,Math.min(.025,P*this.scale/4),.01))}}),o&&a.multiplyScalar(100/o);const c=h=>{const u=h.diagnostics,d=f=>typeof f=="number"?f.toFixed(3):"未知";return`${h.label}
全身负距离: ${d(u.full_depth_cm)} cm；双足: ${d(u.feet_depth_cm)} cm
验收（报告）: ${u.static_recovery_pass??"未知"}；保留（报告）: ${u.all_required_kept??"未知"}`};this.details.textContent=`${c(t)}

${c(this.selected)}

灰点：报告中的历史接触标记
${this.link} 材料点平均 dx (cm): ${o?a.toArray().map(h=>h.toFixed(3)).join(", "):"无网格采样"}
箭头显示倍率: ${this.scale}×`}bounds(t){this.reference&&t.expandByObject(this.group)}terrainVisible(t){this.group.children.forEach(e=>{e!==this.reference&&(e.visible=t)})}}class Jx{constructor(t,e,n){qt(this,"group",new ke);qt(this,"phases",[]);qt(this,"selected",0);qt(this,"marker",null);qt(this,"details",null);qt(this,"rawGroup",new ke);qt(this,"showRaw",!0);this.scene=t,this.jump=e,this.focus=n,t.add(this.group)}clear(){Sn(this.group),this.rawGroup.clear(),this.marker=null}setup(t){this.clear(),this.phases=(t==null?void 0:t.kind)==="support_motion"?t.phases??[]:[],this.selected=0;const e=document.getElementById("reviewPanel");if(!this.phases.length)return;e.hidden=!1;const n=document.createElement("p");n.textContent=t.notice,e.append(n);const s=document.createElement("label");s.className="stack-field";const r=document.createElement("span");r.textContent="持续接触阶段";const a=document.createElement("select");a.setAttribute("aria-label","持续接触阶段"),this.phases.forEach((l,h)=>a.add(new Option(`${l.start}–${l.end} ${l.part}`,String(h)))),a.onchange=()=>{this.selected=Number(a.value),this.draw(),this.jump(this.phases[this.selected].start),this.focusSelected()},s.append(r,a),e.append(s);const o=document.createElement("label");o.className="toggle";const c=document.createElement("input");c.type="checkbox",c.checked=this.showRaw,c.onchange=()=>{this.showRaw=c.checked,this.rawGroup.visible=this.showRaw},o.append(c,document.createTextNode("显示原始 rollout 轨迹")),e.append(o),this.details=document.createElement("p"),e.append(this.details),this.draw()}dot(t,e,n){const s=new ge(new pi(n,10,8),new Ke({color:e,depthTest:!1}));return s.position.set(...t),s.renderOrder=20,this.group.add(s),s}draw(){this.clear();const t=this.phases[this.selected];if(!t)return;const e=t.part==="left_foot"?15754313:3254232,n=l=>l.map(h=>new D(...h));this.group.add(this.rawGroup),t.rollouts.forEach(l=>{const h=new qs(new Le().setFromPoints(n(l)),new zn({color:e,transparent:!0,opacity:.12,depthTest:!1,depthWrite:!1}));h.renderOrder=15,this.rawGroup.add(h)}),this.rawGroup.visible=this.showRaw;const s=n(t.aggregate),r=new sv;for(let l=1;l<s.length;l++)s[l].distanceToSquared(s[l-1])>1e-12&&r.add(new Uu(s[l-1],s[l]));if(r.curves.length){const l=new ge(new el(r,Math.max(8,s.length*2),.0015,6,!1),new Ke({color:e,depthTest:!1,depthWrite:!1}));l.renderOrder=16,this.group.add(l)}else this.dot(t.aggregate[0],e,.003);const a=s[0],c=s.at(-1).clone().sub(a);if(c.z=0,c.length()>1e-6){const l=new Zi(c.clone().normalize(),a,c.length(),e,Math.min(.004,c.length()/6),.0015);l.traverse(h=>{h.material&&(h.material.depthTest=!1)}),l.renderOrder=18,this.group.add(l)}this.marker=this.dot(t.aggregate[0],16777215,.0025),this.details&&(this.details.textContent=`聚合净位移 ${t.aggregate_net_cm.toFixed(2)} cm；原始 rollout 中位数 ${t.rollout_median_net_cm.toFixed(2)} cm。亮色宽线：聚合；淡色细线：原始执行；同一固定材料点。`)}update(t){const e=this.phases[this.selected];!e||!this.marker||(this.marker.visible=t>=e.start&&t<=e.end,this.marker.visible&&this.marker.position.set(...e.aggregate[t-e.start]))}focusSelected(){const t=this.phases[this.selected];t&&this.focus(t.aggregate)}}class Zx{constructor(t,e){qt(this,"group",new ke);qt(this,"review");qt(this,"gain",20);qt(this,"frame",0);qt(this,"details",null);this.focus=e,t.add(this.group)}clear(){Sn(this.group)}setup(t){if(this.clear(),this.review=t,this.details=null,(t==null?void 0:t.kind)!=="support_slip")return;const e=document.getElementById("reviewPanel");e.hidden=!1;const n=document.createElement("p");n.textContent=t.notice,e.append(n);const s=document.createElement("label");s.className="stack-field",s.append(document.createTextNode("位移箭头倍率（不改变统计值）"));const r=document.createElement("input");r.type="number",r.min="1",r.max="100",r.value=String(this.gain),r.onchange=()=>{this.gain=Math.max(1,Math.min(100,Number(r.value)||1)),this.update(this.frame)},s.append(r),e.append(s);const a=document.createElement("button");a.textContent="聚焦当前接触点",a.onclick=()=>{var c,l;const o=((l=(c=this.review)==null?void 0:c.slip_frames)==null?void 0:l[this.frame])??[];o.length&&this.focus(o.map(h=>new D(...h.position)))},e.append(a),this.details=document.createElement("p"),e.append(this.details)}update(t){var h,u,d;if(this.frame=t,this.clear(),((h=this.review)==null?void 0:h.kind)!=="support_slip")return;const e=((u=this.review.slip_frames)==null?void 0:u[t])??[],n=["左脚","右脚","左手","右手","左膝","右膝"],s=f=>`${f.part}:${f.surface}`,r=new Map;e.forEach(f=>r.set(s(f),Math.min(r.get(s(f))??1/0,f.motion_cm))),e.forEach(f=>{const g=f.motion_cm===r.get(s(f))?3594650:15967552,_=new D(...f.position),m=new D(...f.delta),p=new ge(new pi(.0015,8,6),new Ke({color:g,depthTest:!1}));p.position.copy(_),p.renderOrder=25,this.group.add(p);const P=m.length()*this.gain;if(P>1e-7){const w=new Zi(m.normalize(),_,P,g,Math.min(.004,P*.25),Math.min(.002,P*.12));w.traverse(y=>{y.material&&(y.material.depthTest=!1),y.renderOrder=25}),this.group.add(w)}});const a=[...r].map(([f,g])=>{const[_,m]=f.split(":").map(Number),p=e.filter(y=>s(y)===f).map(y=>y.motion_cm).sort((y,N)=>y-N),P=Math.floor(p.length/2),w=p.length%2?p[P]:(p[P-1]+p[P])/2;return`${n[_]}·面${m}：最低几何运动 ${g.toFixed(3)} / 中位 ${w.toFixed(3)} / 最大 ${p.at(-1).toFixed(3)} cm`}),o=(d=this.review.support_frames)==null?void 0:d[t],c={no_contact:"无有效接触",unloaded:"接触但卸载",load_bearing:"承重",unknown:"未知"},l=o?o.map(f=>{var g,_;return`${n[f.part]} ${c[f.load_state]??"未知"}：${((g=f.normal_force_n)==null?void 0:g.toFixed(1))??"未知"} N，承重点相对切向速度 ${((_=f.loaded_speed_cm_s)==null?void 0:_.toFixed(2))??"未知"} cm/s`}).join("；"):"承重滑移：未知";this.details&&(this.details.textContent=(e.length?`${t}→${t+1}；${a.join("；")}。`:"此帧无可测几何区间，不能记作零滑移。")+l+"。")}}class Qx{constructor(t){qt(this,"reference",null);qt(this,"terrain",null);qt(this,"currentTerrain",null);qt(this,"data");qt(this,"materials",[]);qt(this,"spacing",1);qt(this,"mode","beside");qt(this,"terrainShown",!0);qt(this,"opacity",1);qt(this,"available",!0);qt(this,"referenceFrame",null);this.scene=t}clear(){this.reference&&this.scene.remove(this.reference),this.materials.forEach(t=>t.dispose()),this.materials=[],this.terrain&&(this.scene.remove(this.terrain),Ai(this.terrain)),this.currentTerrain&&(this.currentTerrain.position.y=0),this.reference=null,this.terrain=null,this.currentTerrain=null,this.data=void 0,this.referenceFrame=null}setup(t,e,n,s){if(this.clear(),this.data=t,this.currentTerrain=n,!t)return;this.reference=e.clone(),this.terrain=s,this.reference.traverse(a=>{if(!a.isMesh)return;const o=c=>{var h;const l=c.clone();return(h=l.color)==null||h.set(5815528),this.materials.push(l),l};a.material=Array.isArray(a.material)?a.material.map(o):o(a.material)});const r=a=>a?new Gn().setFromObject(a).getSize(new D).y:0;this.spacing=Math.max(1,(r(n)+r(s))/4+.5),this.scene.add(this.reference),this.terrain&&this.scene.add(this.terrain),this.setMode(this.mode)}setMode(t){this.mode=t,this.materials.forEach(e=>{e.transparent=t==="overlay",e.opacity=t==="overlay"?.4:1,e.depthWrite=t!=="overlay"}),this.currentTerrain&&(this.currentTerrain.position.y=this.offset)}get layout(){return this.mode}get offset(){return this.data&&this.mode==="beside"?this.spacing:0}update(t,e){if(!this.data||!this.reference)return;e.position.y+=this.offset;const n=(this.data.qpos.length-1)/this.data.fps;if(this.available=t<=n+1e-8,this.reference.visible=this.available,this.referenceFrame=this.available?Math.min(this.data.qpos.length-1,Math.round(t*this.data.fps)):null,this.referenceFrame!==null){const s=this.data.qpos[this.referenceFrame];this.reference.position.set(s[0],s[1]-this.offset,s[2]),this.reference.quaternion.set(s[4],s[5],s[6],s[3]),this.data.joint_names.forEach((r,a)=>this.reference.setJointValue(r,s[7+a])),this.reference.updateMatrixWorld(!0)}this.terrain&&(this.terrain.position.y=-this.offset),this.display(this.terrainShown,this.opacity)}display(t,e){this.terrainShown=t,this.opacity=e,this.terrain&&(this.terrain.visible=t&&this.available&&(this.mode==="beside"||!this.currentTerrain),this.terrain.traverse(n=>{if(!n.isMesh)return;(Array.isArray(n.material)?n.material:[n.material]).forEach(r=>{r.transparent=e<1,r.opacity=e,r.depthWrite=e===1})}))}bounds(t,e=!0){var n,s;(n=this.reference)!=null&&n.visible&&t.expandByObject(this.reference),e&&((s=this.terrain)!=null&&s.visible)&&t.expandByObject(this.terrain)}}const Ju=document.querySelector("#app");if(!Ju)throw new Error("missing #app root");Yx(Ju);$x();const Tn=document.querySelector("#scene"),En=document.querySelector("#timeline"),Di=new z0({canvas:Tn,antialias:!0,preserveDrawingBuffer:!0});Di.setPixelRatio(Math.min(window.devicePixelRatio,2));Di.outputColorSpace=Ne;Di.toneMapping=iu;Di.toneMappingExposure=1.08;Di.shadowMap.enabled=!1;const Oe=new Lu;Oe.background=new Jt(725014);Oe.fog=new Jc(725014,9,20);Oe.up.set(0,0,1);const $e=new tn(42,1,.01,100);$e.up.set(0,0,1);$e.position.set(3.2,-4.5,2.7);const wn=new Rv($e,Tn);wn.target.set(0,0,.9);wn.enableDamping=!0;Oe.add(new vv(16055295,1515562,2.4));const Zu=new Hu(16777215,3.1);Zu.position.set(3,-4,7);Oe.add(Zu);const Qu=new Tv(14,28,3358796,1910576);Qu.rotation.x=Math.PI/2;Oe.add(Qu);let ct=null,Ge=null,ze=null;const td=new Zx(Oe,i=>{const t=new Gn().setFromPoints(i).getBoundingSphere(new gi),e=$e.position.clone().sub(wn.target).normalize();wn.target.copy(t.center),$e.position.copy(t.center).addScaledVector(e,Math.max(.45,t.radius*5)),wn.update()});let gr=new ke;Oe.add(gr);const Yn=new sx(Tn,$e);Oe.add(Yn.handles,Yn.restoreGhosts);let Ii=new ke;Oe.add(Ii);let jn=new ke;Oe.add(jn);let yn=null,Ce=null,fe=0,fr=!1,eu=performance.now(),cr=0,Oc="all",ed="",nd=!0,_r=!1,Os=!1,As=null,vr=!1,xr=!1,$i=!1,ya=null,La=Promise.resolve(),Na=[];function es(){return vr||xr||$i||(ct==null?void 0:ct.generation.status)==="running"}async function wr(i){if(es())return null;xr=!0,zs.cancel(),Ui();try{return await La,await i()}catch(t){return an(String(t),!0),null}finally{xr=!1,Ui()}}const yr=new Kx(Oe,i=>{ct&&(ct.qpos=[i],mn(0))}),$n=new Qx(Oe),kc=new Jx(Oe,i=>mn(i),i=>{const t=i.map(r=>new D(...r)),e=new Gn().setFromPoints(t).getCenter(new D),n=$e.position.clone().sub(wn.target).normalize(),s=t.at(-1).clone().sub(t[0]);s.z=0,wn.target.copy(e),$e.position.copy(e).addScaledVector(n,s.length()<.05?.48:.95),wn.update()}),Da=[1619620,6869905,15754313,16758087,5213439,11958502,3254232,14703261],id={LHEE:"left_foot",LTOE:"left_foot",RHEE:"right_foot",RTOE:"right_foot",LH:"left_hand",RH:"right_hand",LK:"left_knee",RK:"right_knee",left_heel:"left_foot",left_toe:"left_foot",right_heel:"right_foot",right_toe:"right_foot",left_hand:"left_hand",right_hand:"right_hand",left_knee:"left_knee",right_knee:"right_knee"};let Ma=NaN;try{Ma=Number(localStorage.getItem("motion-edit.timeline-height"))}catch{}let Cs=Number.isFinite(Ma)&&Ma>0?Ma:window.innerWidth<=760?200:230;function rl(i,t=!1){if(Cs=Math.max(150,Math.min(window.innerHeight*.48,Math.round(i))),document.documentElement.style.setProperty("--timeline-height",`${Cs}px`),t)try{localStorage.setItem("motion-edit.timeline-height",String(Cs))}catch{}hl()}rl(Cs);async function Ia(){const i=await Ln("/api/recent-motions"),t=X("recentMotionList");X("recentMotionCount").textContent=String(i.items.length);const e=i.items.map(n=>{const s=document.createElement("button");s.type="button",s.className=`recent-motion-item${n.motion_id===i.active_motion_id?" active":""}`,s.dataset.motionKey=n.motion_id,s.setAttribute("aria-pressed",String(n.motion_id===i.active_motion_id));const r=document.createElement("span");r.className="recent-motion-marker";const a=document.createElement("span");a.className="recent-motion-copy";const o=document.createElement("strong");o.textContent=n.label;const c=document.createElement("small");return c.textContent=n.provenance,a.append(o,c),s.append(r,a),s.onclick=()=>{ja(n.motion_id)},s});return t.replaceChildren(...e),i.items}function ty(i){document.querySelectorAll(".recent-motion-item").forEach(t=>{const e=t.dataset.motionKey===i;t.classList.toggle("active",e),t.setAttribute("aria-pressed",String(e))})}async function ja(i,t=!1){if(!(es()||(ct==null?void 0:ct.motion_id)===i)){vr=!0,Wn(!1),zs.cancel(),Ui(),document.querySelectorAll(".recent-motion-item").forEach(e=>e.disabled=!0);try{an(t?"Opening generated motion":"Opening motion",!1,!0),await La;const e=await Ln("/api/session/load",{method:"POST",body:JSON.stringify({motion_id:i})});fe=0,await Ya(e,!0),await Ia(),Mr(),t&&an("Generated candidate opened · native validation required")}catch(e){an(String(e),!0)}finally{vr=!1,Ui()}}}async function sd(){var t,e;an("Loading motions",!1,!0),X("retryLoad").hidden=!0,Na=(await Ln("/api/motions")).motions;let i=null;try{i=await Ln("/api/session")}catch(n){if(!(n instanceof ju)||n.status!==404)throw n}if(i)await Ya(i,!0),await Ia(),Mr();else{const s=((t=(await Ia())[0])==null?void 0:t.motion_id)||((e=Na.find(r=>r.ready))==null?void 0:e.motion_id);s?await ja(s):an("No motion available. Open a registered motion or a playback file.",!1,!0)}}function rd(){const i=X("motionSearch").value.trim().toLowerCase(),t=Na.filter(n=>`${n.motion_id} ${n.label} ${n.provenance}`.toLowerCase().includes(i)),e=X("motionPickerList");e.replaceChildren();for(const n of t){const s=document.createElement("button");s.className="motion-picker-item",s.disabled=!n.ready;const r=document.createElement("strong");r.textContent=n.label;const a=document.createElement("small");a.textContent=`${n.motion_id} · ${n.provenance} · ${n.ready?"可打开":"文件缺失"}`,s.append(r,a),s.onclick=()=>{X("motionPicker").close(),ja(n.motion_id)},e.append(s)}t.length||(e.textContent="没有匹配的轨迹")}X("openMotionBtn").onclick=async()=>{if(!es())try{Na=(await Ln("/api/motions")).motions,X("motionSearch").value="",rd(),X("motionPicker").showModal(),X("motionSearch").focus()}catch(i){an(String(i),!0)}};X("closeMotionPicker").onclick=()=>X("motionPicker").close();X("motionSearch").oninput=rd;X("retryLoad").onclick=()=>{sd().catch(ad)};function ad(i){an(String(i),!0),X("retryLoad").hidden=!1}async function Ya(i,t=!1){var r,a;const e=Ce==null?void 0:Ce.handle_id,n=ct;ct=i,Ce=e&&i.edit_handles.find(o=>o.handle_id===e)||null,fe=Math.min(fe,i.qpos.length-1),t&&((r=i.review)==null?void 0:r.kind)==="support_motion"&&((a=i.review.phases)!=null&&a.length)&&(fe=i.review.phases[0].start),document.body.classList.toggle("review-mode",!!i.review),document.body.classList.toggle("playback-only",i.read_only),X("playbackNotice").hidden=!i.read_only,i.contact_force.mask_status&&i.contact_force.mask_status!=="verified_newton_primary_faces"?(X("playbackNotice").hidden=!1,X("playbackNotice").textContent="当前接触状态未知：记录的力与旧掩码未经同帧 Newton／主表面验证，不作为有效接触显示。编辑手柄表示已有编辑意图。"):X("playbackNotice").textContent="只读轨迹：接触状态以已验证的 Newton 数据为准；无接触层时不显示编辑手柄。",ty(i.motion_id);const s=i.motion_id;if(X("motionLabel").textContent=s,X("viewportMotion").textContent=s,(t||!n)&&(X("fpsInput").value=String(i.fps)),X("anchorCount").textContent=i.read_only?"Playback only":`${i.edit_handles.length} handles`,X("editCount").textContent=i.read_only?i.review?"Contact unknown":"No contact layer":`${i.pending_edit_count} edits`,X("undoBtn").disabled=!i.can_undo,X("redoBtn").disabled=!i.can_redo,X("planPath").value=i.settings.edit_plan_path||"",X("outputMotion").value=i.settings.output_motion_path||"",X("outputLayer").value=i.settings.output_contact_layer||"",X("outputMotionId").value=i.settings.output_motion_id||"",X("registerMotion").checked=i.settings.register_motion,X("overwriteOutput").checked=i.settings.overwrite,X("sourceLayer").textContent=i.settings.source_contact_layer||"None",X("planStatus").textContent=i.read_only?"Read-only kinematic reference":i.plan?`${i.plan.status} · ${i.plan.edit_count} edits`:"No plan saved",cl(i.generation),ly(),Bs(),t)try{await ey(i)}catch(o){throw ct=null,Ce=null,Wn(!1),Yn.clear(),Sn(jn),X("retryLoad").hidden=!1,Ui(),o}else $a(Ce);mn(fe)}async function ey(i){var t,e,n,s;an("Loading scene",!1,!0),$i=!0,Ui();try{const r=new Bu,a=new Promise((g,_)=>{r.onLoad=()=>g(),r.onError=m=>_(new Error(`failed to load robot asset: ${m}`))}),o=new Qv(r);o.loadMeshCb=(g,_,m)=>{if(g.toLowerCase().endsWith(".obj")){new Wo(_).load(g,p=>m(p),void 0,p=>m(new ke,p));return}m(new ke,new Error(`unsupported URDF mesh: ${g}`))};const[c,l]=await Promise.allSettled([o.loadAsync(i.robot_urdf_url),a]);if(c.status==="rejected"||l.status==="rejected")throw c.status==="fulfilled"&&Ai(c.value),c.status==="rejected"?c.reason:l.reason;const h=c.value;let u=null,d=null;try{i.terrain_obj_url&&(u=await new Wo().loadAsync(i.terrain_obj_url)),(e=(t=i.review)==null?void 0:t.comparison)!=null&&e.terrain_obj_url&&(d=await new Wo().loadAsync(i.review.comparison.terrain_obj_url))}catch(g){throw Ai(h),u&&Ai(u),g}yr.setup(void 0,null,null,[]),$n.clear(),Ge&&(Oe.remove(Ge),Ai(Ge)),ze&&(Oe.remove(ze),Ai(ze)),Sn(gr),Yn.clear(),Sn(Ii),Sn(jn),Ce=null,yn&&(Oe.remove(yn),Ai(yn),yn=null),Ge=h,ze=u;let f=0;if(Ge.traverse(g=>{g.isMesh&&f++}),Tn.dataset.robotMeshes=String(f),Oe.add(Ge),ze){const g=new rv({color:5858672,roughness:.86,metalness:.03}),_=new Set;ze.traverse(m=>{m.isMesh&&((Array.isArray(m.material)?m.material:[m.material]).forEach(p=>_.add(p)),m.material=g)}),_.forEach(m=>m.dispose()),Oe.add(ze)}$i=!1,yr.setup(i.review,Ge,ze,i.joint_names),kc.setup(i.review),td.setup(i.review),$n.setup((n=i.review)==null?void 0:n.comparison,Ge,ze,d),ry(),ld(),iy(),ny(),sy(),Qi(),Ka(),((s=i.review)==null?void 0:s.kind)==="support_motion"&&kc.focusSelected(),Ja(),Mr()}finally{$i=!1,Ui()}}function ny(){if(!ct)return;const i=ct.qpos.map(t=>new D(t[0],t[1],t[2]));yn=new qs(new Le().setFromPoints(i),new zn({color:11450306,transparent:!0,opacity:.45})),yn.visible=X("rootPathToggle").checked,Oe.add(yn)}function iy(){if(ct)for(const i of ct.surfaces){if(i.surface_id==="terrain_ground_z0")continue;const t=new D(...i.normal).normalize().multiplyScalar(.002),e=i.metadata.polygon_world;let n;if(e!=null&&e.length&&e.length>=3)n=e.map(o=>new D(o[0],o[1],o[2]).add(t));else{const o=new D(...i.origin),c=new D(...i.tangent_u),l=new D(...i.tangent_v),[h,u]=i.bounds.u,[d,f]=i.bounds.v;n=[o.clone().addScaledVector(c,h).addScaledVector(l,d),o.clone().addScaledVector(c,u).addScaledVector(l,d),o.clone().addScaledVector(c,u).addScaledVector(l,f),o.clone().addScaledVector(c,h).addScaledVector(l,f)].map(g=>g.add(t))}const s=[];for(let o=1;o<n.length-1;o++)s.push(0,o,o+1);const r=new Le().setFromPoints(n);r.setIndex(s),r.computeVertexNormals();const a=new ge(r,new Ke({color:5087165,transparent:!0,opacity:.08,side:dn,depthWrite:!1}));a.userData.surface=i,gr.add(a)}}function od(i){return String(i.metadata.surface_editor_status||"bound")}function Ua(i){return fe>=i.start_frame&&fe<i.end_frame}function Fa(i,t){const e=X("positionOffset");if(!i){e.classList.add("disabled"),e.classList.remove("edited"),X("offsetU").textContent="—",X("offsetV").textContent="—";return}const{u:n,v:s}=ax(i,t);e.classList.remove("disabled"),e.classList.toggle("edited",Math.max(Math.abs(n),Math.abs(s))>rx),X("offsetU").textContent=Zh(n),X("offsetV").textContent=Zh(s)}function Oa(i=nd){if(!ct)return[];const t=ed.trim().toLowerCase();return ct.edit_handles.filter(e=>{const n=od(e);if(i&&!Ua(e)||Oc!=="all"&&n!==Oc)return!1;const s=Array.isArray(e.metadata.source_bodies)?e.metadata.source_bodies.join(" "):"",r=Array.isArray(e.metadata.patch_roles)?e.metadata.patch_roles.join(" "):"";return!t||`${e.handle_id} ${e.body} ${e.surface_id} ${e.object_id||""} ${s} ${r}`.toLowerCase().includes(t)})}function Qi(){if(!ct)return;const i=new Set(Oa().map(t=>t.handle_id));Ce&&!i.has(Ce.handle_id)&&(Ce=null,X("selection").className="selection empty",X("selection").textContent="None",Fa(null),Sn(jn),ks()),Yn.rebuild({handles:ct.edit_handles,visibleHandleIds:i,selectedHandle:Ce,radius:Number(X("handleSize").value)/1e3}),Yn.setVisible(X("handleToggle").checked),cd(),ul()}function cd(){const i=Oa(!1),t=Oa().length,e=!!es()||!ct||ct.read_only||!i.length;X("prevAnchor").disabled=e,X("nextAnchor").disabled=e;const n=i.findIndex(a=>a.handle_id===(Ce==null?void 0:Ce.handle_id)),s=i.length?`${i.length} matched · ${t} shown${n<0?"":` · Selected ${n+1}/${i.length}`}`:"No matching episodes",r=X("episodeBrowseStatus");r.textContent!==s&&(r.textContent=s)}function al(){zs.cancel(),Qi(),Bs()}function sy(){if(!ct)return;Sn(Ii),Tn.dataset.contactSample="point-force";const i=ct.contact_force.part_order.length;Tn.dataset.contactPartSlots=String(i);for(let t=0;t<i;t++){const e=new ke,n=new Ke({color:Da[t%Da.length],depthTest:!0,transparent:!0}),s=new ge(new pi(.014,14,10),n),r=new ge(new js(.006,.006,1,8),n),a=new ge(new tl(.022,.055,10),n);e.add(s,r,a),e.userData.point=s,e.userData.shaft=r,e.userData.head=a,e.userData.material=n,Ii.add(e)}ks()}function ks(){if(!ct)return;const i=ct;Ii.visible=X("contactSampleToggle").checked;const t=i.contact_force.positions[fe]||[],e=i.contact_force.forces[fe]||[],n=i.contact_force.masks[fe]||[],s=i.contact_force.position_valid[fe]||[];let r=0;Ii.children.forEach((a,o)=>{const c=a,l=o<t.length&&o<e.length&&!!n[o]&&!!s[o];if(c.visible=l,!l)return;r++;const h=new D(...e[o]),u=h.length(),d=Number(X("forceScale").value)/100,f=Math.min(.9,u/1200*d),g=Math.min(.055,f*.35),_=Math.max(.001,f-g);c.position.set(...t[o]),u>1e-5&&c.quaternion.setFromUnitVectors(new D(0,1,0),h.normalize());const m=id[i.contact_force.part_order[o]]||i.contact_force.part_order[o],p=!Ce||Ce.body===m;c.scale.setScalar(Ce&&p?1.35:1);const P=c.userData.material;P.opacity=p?1:.22;const w=c.userData.shaft,y=c.userData.head;w.scale.set(1,_,1),w.position.set(0,_/2,0),y.scale.set(1,g/.055,1),y.position.set(0,_+g/2,0),w.visible=u>1e-5,y.visible=u>1e-5}),Tn.dataset.visibleContactParts=String(r),Tn.dataset.selectedContactBody=(Ce==null?void 0:Ce.body)||""}function ld(){if(!ct||!Ge||$i)return;const i=ct.qpos[fe];if(!i)return;const t=Ge.position.clone();if(Ge.position.set(i[0],i[1],i[2]),Ge.quaternion.set(i[4],i[5],i[6],i[3]),ct.joint_names.forEach((e,n)=>{var s;return(s=Ge.setJointValue)==null?void 0:s.call(Ge,e,i[7+n])}),yr.update(),$n.update(fe/ct.fps,Ge),yn&&(yn.position.y=$n.offset),X("followRobot").checked){const e=Ge.position.clone().sub(t);$e.position.add(e),wn.target.add(e)}kc.update(fe),td.update(fe),ay()}function mn(i){ct!=null&&ct.qpos.length&&(Number.isFinite(i)||(i=fe),fe=Math.max(0,Math.min(ct.qpos.length-1,Math.round(i))),X("frameInput").max=String(ct.qpos.length-1),X("frameInput").value=String(fe),X("frameTotal").textContent=`/ ${ct.qpos.length-1}`,X("viewportFrame").textContent=`Frame ${fe}`,X("viewportTime").textContent=`${(fe/ct.fps).toFixed(2)} s`,ld(),ks(),Qi(),Bs())}function ry(){var a,o,c;const i=ct==null?void 0:ct.review,t=i==null?void 0:i.collection;if(X("collectionPanel").hidden=!t,!t)return;const e=X("reviewCase"),n=X("reviewReference");e.replaceChildren(),n.replaceChildren(new Option("不对比","-1")),t.cases.forEach(l=>{e.add(new Option(l.label,String(l.index))),l.index!==t.case_index&&n.add(new Option(l.label,String(l.index)))}),e.value=String(t.case_index),n.value=String(t.reference_index);const s=X("reviewLayout");s.value=$n.layout,s.parentElement.hidden=!i.comparison;const r=X("reviewSegment");r.replaceChildren(),(a=i.segments)==null||a.forEach(l=>r.add(new Option(`${l.label} · ${l.start}–${l.end}`,String(l.start)))),r.parentElement.hidden=!((o=i.segments)!=null&&o.length),X("reviewWorst").hidden=!((c=i.depth_mm)!=null&&c.length)}function ay(){var n,s;const i=ct==null?void 0:ct.review;if(!(i!=null&&i.collection))return;X("comparisonClock").textContent=i.comparison?`按时间对齐（起点 t=0，最近采样帧）：当前 ${fe}；参考 ${$n.referenceFrame??"已结束，不显示"}。不自动匹配接触事件。`:"单轨迹回放",X("scene").dataset.referenceFrame=String($n.referenceFrame??"none");const t=(n=i.depth_mm)==null?void 0:n[fe];X("reviewMetrics").textContent=t===void 0?"当前帧穿透诊断：未提供":`报告穿透深度：${t.toFixed(2)} mm（非接触或承重判定）`;const e=(s=i.segments)==null?void 0:s.find(r=>fe>=r.start&&fe<=r.end);X("reviewSegment").value=e?String(e.start):""}async function ol(i,t,e=0,n,s=!1){return wr(async()=>{Wn(!1),an("Loading playback",!1,!0);const r=await Ln("/api/review/load",{method:"POST",body:JSON.stringify({path:i,terrain:t,case_index:e,reference_index:n})});s||(fe=0),await Ya(r,!0),X("reviewPath").value=i,X("reviewTerrain").value=t||""})}X("reviewCase").onchange=()=>{var e;const i=(e=ct==null?void 0:ct.review)==null?void 0:e.collection;if(!i)return;const t=Number(X("reviewCase").value);X("reviewCase").value=String(i.case_index),ol(i.path,i.terrain_override,t)};X("reviewReference").onchange=()=>{var e;const i=(e=ct==null?void 0:ct.review)==null?void 0:e.collection;if(!i)return;const t=Number(X("reviewReference").value);X("reviewReference").value=String(i.reference_index),ol(i.path,i.terrain_override,i.case_index,t,!0)};X("reviewLayout").onchange=()=>{$n.setMode(X("reviewLayout").value),mn(fe),Ka()};X("reviewSegment").onchange=()=>{Wn(!1),mn(Number(X("reviewSegment").value))};X("reviewWorst").onclick=()=>{var t;const i=(t=ct==null?void 0:ct.review)==null?void 0:t.depth_mm;i!=null&&i.length&&(Wn(!1),mn(i.reduce((e,n,s)=>n>i[e]?s:e,0)))};function oy(){return Yu(En,(ct==null?void 0:ct.contact_force.part_order.length)??8)}function cy(i,t){return lx(i,t,(ct==null?void 0:ct.qpos.length)??1)}function Bs(){ux({canvas:En,session:ct,frame:fe,selectedHandle:Ce,stableCuts:hd(),partColors:Da})}function hd(){var t,e;if(!ct)return[];const i=new Set;return(e=(t=ct.review)==null?void 0:t.segments)==null||e.forEach(n=>{i.add(n.start),i.add(n.end)}),ct.graph.transitions.forEach(n=>{var r;i.add(n.start_frame),i.add(Math.max(n.start_frame,n.end_frame-1));const s=(r=n.metadata)==null?void 0:r.stable_anchor_frames;Array.isArray(s)&&s.forEach(a=>i.add(Number(a)))}),[...i].filter(n=>Number.isFinite(n)).sort((n,s)=>n-s)}function ly(){ct&&(X("partLegend").innerHTML=ct.contact_force.part_order.map((i,t)=>`<span><b style="background:#${Da[t].toString(16).padStart(6,"0")}"></b>${i}</span>`).join(""))}function $a(i){Ce=i;const t=X("selection");if(!i){t.className="selection empty",t.textContent="None",Fa(null),Sn(jn),ks(),Qi(),Bs();return}t.className="selection",t.innerHTML=`<strong>${i.body}</strong><code>${i.handle_id}</code><dl><dt>Frames</dt><dd>${i.start_frame}–${i.end_frame}</dd><dt>Surface</dt><dd>${i.surface_id}</dd><dt>Members</dt><dd>${String(i.metadata.member_count||i.member_anchor_ids.length)}</dd><dt>Status</dt><dd>${od(i)}</dd></dl>`,Fa(i),hy(i),ks(),Qi(),Bs(),ul()}function hy(i){Sn(jn),jn.visible=X("guideToggle").checked;const t=new D(...i.world_position),e=[[i.surface_tangent_u,15754313],[i.surface_tangent_v,6869905],[i.surface_normal,5213439]];for(const[n,s]of e){const r=new D(...n).normalize().multiplyScalar(.14),a=new qs(new Le().setFromPoints([t.clone().addScaledVector(r,-1),t.clone().add(r)]),new zn({color:s}));jn.add(a)}}const zs=new ex({canvas:Tn,controls:wn,layer:Yn,getSession:()=>ct,isBusy:es,getSelectedHandle:()=>Ce,selectHandle:$a,updatePositionOffset:Fa,rebuildHandles:Qi,restoreHandle:async i=>!!await Vs("/api/session/restore-handle",{handle_id:i.handle_id,mode:X("modeSelect").value}),moveHandle:async(i,t)=>!!await Vs("/api/session/move-handle",{handle_id:i.handle_id,requested_world_position:t.toArray(),mode:X("modeSelect").value})});function Ka(i=!1){const t=new Gn;if(Ge&&t.expandByObject(Ge),!i&&(ze!=null&&ze.visible)&&t.expandByObject(ze),i||yr.bounds(t),$n.bounds(t,!i),t.isEmpty())return;const e=t.getBoundingSphere(new gi),n=Math.min(Ri.degToRad($e.fov/2),Math.atan(Math.tan(Ri.degToRad($e.fov/2))*$e.aspect)),s=Math.max(.4,e.radius*1.15/Math.sin(n));wn.target.copy(e.center),$e.position.copy(e.center).addScaledVector(new D(1.8,-2.4,1.35).normalize(),s),$e.far=Math.max(100,s+e.radius*4),$e.updateProjectionMatrix(),Oe.fog=null,wn.update()}function Mr(){ya!==null&&window.clearTimeout(ya),ya=null,X("sceneStatus").classList.add("hidden")}function an(i,t=!1,e=!1){Mr();const n=X("sceneStatus");n.textContent=i,n.classList.remove("hidden"),n.classList.toggle("error",t),n.setAttribute("role",t?"alert":"status"),!t&&!e&&(ya=window.setTimeout(Mr,3e3))}function Ja(){const i=X("terrainToggle").checked;ze&&(ze.visible=i),yr.terrainVisible(i);const t=Number(X("terrainOpacity").value);ze==null||ze.traverse(e=>{e.isMesh&&(Array.isArray(e.material)?e.material:[e.material]).forEach(n=>{n.transparent=t<1,n.opacity=t,n.depthWrite=t===1})}),$n.display(i,t),gr.visible=X("surfaceToggle").checked,Ii.visible=X("contactSampleToggle").checked,Yn.setVisible(X("handleToggle").checked),jn.visible=X("guideToggle").checked,yn&&(yn.visible=X("rootPathToggle").checked),Tn.dataset.terrainVisible=String((ze==null?void 0:ze.visible)??!1),Tn.dataset.surfacesVisible=String(gr.visible)}function uy(){return{edit_plan_path:X("planPath").value,output_motion_path:X("outputMotion").value,output_contact_layer:X("outputLayer").value,output_motion_id:X("outputMotionId").value,register_motion:X("registerMotion").checked,overwrite:X("overwriteOutput").checked}}function Za(){const i=JSON.stringify(uy()),t=La.then(()=>Ln("/api/session/settings",{method:"PUT",body:i}));return La=t.catch(()=>{}),t.then(e=>(ct=e,e))}function ud(){As!==null&&window.clearTimeout(As),As=null}function dd(){As===null&&(As=window.setTimeout(async()=>{try{const i=await Ln("/api/session/generation");cl(i),As=null,i.status==="running"?dd():i.status==="succeeded"&&(X("planStatus").textContent="generated",i.output_motion_id?await ja(i.output_motion_id,!0):await Ia())}catch(i){ud(),an(String(i),!0),X("retryLoad").hidden=!1}},900))}function Ui(){const i=!!es(),t=!!(ct!=null&&ct.read_only),e=!!ct&&!t;document.querySelectorAll('[data-page="contact"] .anchor-browser input,[data-page="contact"] .anchor-browser select,[data-page="contact"] .anchor-browser button,[data-page="output"] input,[data-page="output"] button').forEach(n=>n.disabled=i||!e),document.querySelectorAll(".recent-motion-item,#openMotionBtn,#reviewOpen,#collectionPanel select,#collectionPanel button").forEach(n=>n.disabled=i),X("undoBtn").disabled=i||!e||!(ct!=null&&ct.can_undo),X("redoBtn").disabled=i||!e||!(ct!=null&&ct.can_redo),X("saveBtn").disabled=i||!e,X("outputMotionId").disabled=i||!e||!X("registerMotion").checked,document.querySelectorAll("#playBtn,#prevBtn,#nextBtn,#prevCut,#nextCut,#frameInput,#fpsInput").forEach(n=>n.disabled=vr||xr||$i||!ct),ct&&ct.qpos.length<2&&(X("playBtn").disabled=!0),X("scene").setAttribute("aria-busy",String(i)),cd()}function cl(i){ct&&(ct.generation=i);const t=i.status==="running",e=!!(ct!=null&&ct.read_only),n=X("generateBtn"),s=X("generationStatus");if(n.disabled=t||!ct||e,n.innerHTML=t?'<i data-lucide="loader-circle" class="spin"></i><span>Generating</span>':'<i data-lucide="wand-sparkles"></i><span>Generate</span>',sl(),s.className=`generation-status ${i.status}`,i.status==="running"){const r={queued:"Queued",reading_plan:"Reading edit plan",validating:"Validating",loading_motion:"Loading motion",contact_laplacian:"Optimizing contact trajectory",writing_intermediates:"Preparing full-body IK",fullbody_ik:"Solving full-body IK",merging_ik:"Merging IK result",writing_output:"Writing motion",registering:"Registering motion",saving_plan:"Saving edit plan"},a=i.started_at===null?"":` · ${Math.max(0,Math.round(Date.now()/1e3-i.started_at))}s`;s.innerHTML="<strong>Generating reference</strong><span></span>",s.querySelector("span").textContent=`${r[i.stage||""]||"Working"}${a}`}else i.status==="succeeded"?(X("overwriteOutput").checked=!0,s.innerHTML=`<strong>Generated${i.warnings.length?` · ${i.warnings.length} warnings`:""}</strong><span></span>`,s.querySelector("span").textContent=i.output_motion_path||"Output written",s.setAttribute("title",i.output_motion_path||"")):i.status==="failed"?(s.innerHTML="<strong>Generation failed</strong><span></span>",s.querySelector("span").textContent=i.error||"Unknown error",s.setAttribute("title",i.error||"")):e?s.innerHTML="<strong>Playback only</strong><span>Kinematic reference · no contact layer</span>":s.innerHTML="<strong>Ready</strong><span>Contact-aware candidate · native validation required</span>";Ui(),t?dd():ud()}function Wn(i){fr=i,fr||(cr=0),X("playBtn").innerHTML=`<i data-lucide="${fr?"pause":"play"}"></i>`,sl()}X("playBtn").onclick=()=>Wn(!fr);X("prevBtn").onclick=()=>{Wn(!1),mn(fe-1)};X("nextBtn").onclick=()=>{Wn(!1),mn(fe+1)};X("frameInput").onchange=i=>mn(Number(i.target.value));async function Vs(i,t){return wr(async()=>{const e=await Ln(i,{method:"POST",body:t===void 0?void 0:JSON.stringify(t)});return await Ya(e),an("Session updated"),e})}X("undoBtn").onclick=()=>{Vs("/api/session/undo")};X("redoBtn").onclick=()=>{Vs("/api/session/redo")};X("saveBtn").onclick=()=>{wr(async()=>{await Za();const i=await Ln("/api/session/save",{method:"POST"});ct&&(ct.plan=i.plan),i.plan&&(X("planStatus").textContent=`${i.plan.status} · ${i.plan.edit_count} edits`),an(`Saved ${i.output_contact_layer}`)})};X("focusBtn").onclick=()=>Ka();X("focusRobot").onclick=()=>Ka(!0);X("terrainOpacity").oninput=Ja;X("terrainToggle").onchange=Ja;X("surfaceToggle").onchange=Ja;X("handleToggle").onchange=i=>Yn.setVisible(i.target.checked);X("contactSampleToggle").onchange=i=>Ii.visible=i.target.checked;X("handleSize").oninput=()=>Qi();X("forceScale").oninput=()=>ks();X("rootPathToggle").onchange=i=>{yn&&(yn.visible=i.target.checked)};X("guideToggle").onchange=i=>jn.visible=i.target.checked;X("anchorSearch").oninput=i=>{ed=i.target.value,al()};X("statusFilter").onchange=i=>{Oc=i.target.value,al()};X("currentOnly").onchange=i=>{nd=i.target.checked,al()};function ll(i){if(es()||!ct||ct.read_only)return;const t=Oa(!1);if(!t.length)return;Wn(!1),zs.cancel();const e=t.findIndex(s=>s.handle_id===(Ce==null?void 0:Ce.handle_id));let n;if(e>=0&&Ua(t[e]))n=t[(e+i+t.length)%t.length];else{const s=i>0?t:t.slice().reverse();n=s.find(Ua)||s.find(r=>i>0?r.start_frame>=fe:r.start_frame<=fe)||s[0]}mn(n.start_frame),$a(n)}X("prevAnchor").onclick=()=>ll(-1);X("nextAnchor").onclick=()=>ll(1);function fd(i){const t=hd();if(!t.length)return;const e=i>0?t:t.slice().reverse(),n=e.find(s=>i>0?s>fe:s<fe)??e[0];mn(n)}X("prevCut").onclick=()=>fd(-1);X("nextCut").onclick=()=>fd(1);function pd(i,t=!1,e=!1){if(!ct)return;const n=En.getBoundingClientRect(),s=oy(),r=i.clientX-n.left,a=i.clientY-n.top,o=cy(r,s);t&&r>=s.labelW&&mn(o);const c=Math.floor((a-s.rulerH)/s.rowH);if(e&&c>=0&&c<ct.contact_force.part_order.length){const u=ct.contact_force.part_order[c],d=id[u]||u,f=ct.edit_handles.filter(g=>g.body===d&&Ua(g));f.length&&$a(f[0])}const l=X("timelineHover"),h=c>=0&&c<ct.contact_force.part_order.length?ct.contact_force.part_order[c]:"Timeline";l.textContent=`${h} · ${$u(o/ct.fps)} · frame ${o}`,l.style.left=`${Math.max(s.labelW+44,Math.min(n.width-72,r))}px`,l.classList.remove("hidden")}En.addEventListener("pointerdown",i=>{ct&&(Wn(!1),Os=!0,En.setPointerCapture(i.pointerId),En.classList.add("scrubbing"),pd(i,!0,!0))});En.addEventListener("pointermove",i=>pd(i,Os,!1));En.addEventListener("pointerup",i=>{Os&&(Os=!1,En.releasePointerCapture(i.pointerId),En.classList.remove("scrubbing"))});En.addEventListener("pointercancel",()=>{Os=!1,En.classList.remove("scrubbing")});En.addEventListener("pointerleave",()=>{Os||X("timelineHover").classList.add("hidden")});document.querySelectorAll("#planPath,#outputMotion,#outputLayer,#outputMotionId,#registerMotion,#overwriteOutput").forEach(i=>{i.dataset.generationSetting="",i.addEventListener("change",()=>{X("outputMotionId").disabled=!X("registerMotion").checked,Za().catch(t=>an(String(t),!0))})});X("validateBtn").onclick=()=>{wr(async()=>{await Za();const i=await Ln("/api/session/validate",{method:"POST"});X("planStatus").textContent=`${i.plan.status}${i.warnings.length?` · ${i.warnings.length} warnings`:""}`,an("ContactEditPlan validated")})};X("generateBtn").onclick=()=>{wr(async()=>{await Za();const i=await Ln("/api/session/generate",{method:"POST",body:JSON.stringify({})});cl(i)})};X("reloadBtn").onclick=()=>{Vs("/api/session/reload")};X("discardBtn").onclick=()=>{Vs("/api/session/discard")};window.addEventListener("keydown",i=>{if(i.code==="Escape"&&zs.active){i.preventDefault(),zs.cancel();return}vr||xr||$i||X("motionPicker").open||i.target.closest("input,select,textarea,button,[contenteditable=true]")||["Space","ArrowLeft","ArrowRight","BracketLeft","BracketRight"].includes(i.code)&&(i.preventDefault(),i.code==="Space"?X("playBtn").click():i.code==="ArrowLeft"||i.code==="ArrowRight"?(Wn(!1),mn(fe+(i.code==="ArrowLeft"?-1:1)*(i.shiftKey?10:1))):ll(i.code==="BracketLeft"?-1:1))});let md=0,gd=0;X("timelineResizer").addEventListener("pointerdown",i=>{_r=!0,md=i.clientY,gd=Cs,X("timelineResizer").setPointerCapture(i.pointerId),document.body.classList.add("resizing-timeline")});X("timelineResizer").addEventListener("pointermove",i=>{_r&&rl(gd+md-i.clientY)});X("timelineResizer").addEventListener("pointerup",i=>{_r&&(_r=!1,X("timelineResizer").releasePointerCapture(i.pointerId),document.body.classList.remove("resizing-timeline"),rl(Cs,!0))});function hl(){const i=Tn.getBoundingClientRect();i.width<=0||i.height<=0||(Di.setSize(i.width,i.height,!1),$e.aspect=i.width/i.height,$e.updateProjectionMatrix(),Bs())}window.addEventListener("resize",hl);hl();function ul(){Yn.updateProjection(Ce)}function _d(i){requestAnimationFrame(_d);const t=Math.min(.1,Math.max(0,(i-eu)/1e3));if(eu=i,fr&&ct&&(cr+=t*vd(!1),cr>=1)){const e=Math.floor(cr);cr-=e,mn((fe+e)%ct.qpos.length)}wn.update(),ul(),Di.render(Oe,$e),Tn.dataset.geometryCount=String(Di.info.memory.geometries)}requestAnimationFrame(_d);function vd(i=!0){const t=X("fpsInput"),e=Number(t.value),n=Number.isFinite(e)&&e>=1?Math.min(240,e):Math.min(240,Math.max(1,(ct==null?void 0:ct.fps)||50));return i&&(t.value=String(n)),n}X("fpsInput").onchange=()=>{vd()};X("timelineResizer").addEventListener("pointercancel",()=>{_r=!1,document.body.classList.remove("resizing-timeline")});X("reviewOpen").onclick=()=>{ol(X("reviewPath").value.trim(),X("reviewTerrain").value.trim()||null)};sd().catch(ad);
