export declare const readBytes: (p: string) => Uint8Array;
export declare const toBytes: (out: any) => Promise<Uint8Array>;
export declare const docxIn: (bytes: Uint8Array) => { buffer: Uint8Array };
export declare function docXmlMd5(
	bytesOrPath: Uint8Array | string,
): Promise<string>;
export declare function isValidDocx(
	bytes: Uint8Array,
): Promise<{ ok: true; size: number } | { ok: false; reason: string }>;
export declare function sofficeConvert(
	srcPath: string,
	fmt: string,
	outDir: string,
	infilter?: string,
): string | null;
export declare function sofficeConvertTo(
	srcPath: string,
	fmt: string,
	wantPath: string,
	infilter?: string,
): boolean;
