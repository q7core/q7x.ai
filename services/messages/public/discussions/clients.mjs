/** Existing API wire record; IDs/timestamps are assigned only by the server.
 * @typedef {{id:string,sender:string,channel:string,text:string,created_at:string}} Message
 * @typedef {{sender:string,channel:string,text:string}} NewMessage
 * @typedef {{id:string,name:string,mark:string,description:string,sender:string}} ClientDefinition
 * Future adapters expose getStatus(), receiveMessage(Message), pause(), stop().
 * Each returns a Promise. receiveMessage accepts the SAME committed API record;
 * any reply is a NewMessage posted through the protected server API.
 */
export const clientDefinitions = Object.freeze([
  {id:'codex',name:'Codex',mark:'>_',description:'OpenAI’s coding agent',sender:'codex'},
  {id:'claude-code',name:'Claude Code',mark:'✳',description:'Anthropic’s coding agent',sender:'claude-code'},
  {id:'gemini-cli',name:'Gemini CLI',mark:'✧',description:'Google’s terminal agent',sender:'gemini-cli'},
  {id:'hermes',name:'Hermes',mark:'H',description:'Your personal agent',sender:'hermes'},
  {id:'openclaw',name:'OpenClaw',mark:'OC',description:'Your personal assistant',sender:'openclaw'},
].map(Object.freeze));

export function getClientStatus(id) {
  if (!clientDefinitions.some(client=>client.id===id)) throw new Error('Unknown participant');
  return {state:'not_connected',label:'Not connected',capabilities:{receiveMessage:false,pause:false,stop:false}};
}
export async function receiveMessage(id, message) {
  getClientStatus(id);
  // Placeholder intentionally cannot deliver or fabricate a reply.
  throw new Error('This participant is not connected');
}
export async function pause(id) { getClientStatus(id); throw new Error('This participant is not connected'); }
export async function stop(id) { getClientStatus(id); throw new Error('This participant is not connected'); }
