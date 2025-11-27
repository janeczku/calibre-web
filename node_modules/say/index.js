const SayLinux = require('./platform/linux.js')
const SayMacos = require('./platform/darwin.js')
const SayWin32 = require('./platform/win32.js')

const MACOS = 'darwin'
const LINUX = 'linux'
const WIN32 = 'win32'

class Say {
  constructor (platform) {
    if (!platform) {
      platform = process.platform
    }

    if (platform === MACOS) {
      return new SayMacos()
    } else if (platform === LINUX) {
      return new SayLinux()
    } else if (platform === WIN32) {
      return new SayWin32()
    }

    throw new Error(`new Say(): unsupported platorm! ${platform}`)
  }
}

module.exports = new Say() // Create a singleton automatically for backwards compatability
module.exports.Say = Say // Allow users to `say = new Say.Say(platform)`
module.exports.platforms = {
  WIN32: WIN32,
  MACOS: MACOS,
  LINUX: LINUX
}
