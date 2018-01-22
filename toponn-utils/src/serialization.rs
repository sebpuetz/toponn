use std::io::{Read, Write};

use toponn::Numberer;

use serde_cbor;
use toml;

use super::{Config, Result};

pub trait TomlRead {
    fn from_toml_read<R>(read: R) -> Result<Config>
    where
        R: Read;
}

impl TomlRead for Config {
    fn from_toml_read<R>(mut read: R) -> Result<Self>
    where
        R: Read,
    {
        let mut data = String::new();
        read.read_to_string(&mut data)?;
        let config: Config = toml::from_str(&data)?;
        Ok(config)
    }
}

pub trait CborRead {
    type Value;

    fn from_cbor_read<R>(read: R) -> Result<Self::Value>
    where
        R: Read;
}

macro_rules! cbor_read {
    ($type: ty) => {
        impl CborRead for $type {
            type Value = $type;

            fn from_cbor_read<R>(read: R) -> Result<$type>
                where R: Read
            {
                let system = serde_cbor::from_reader(read)?;
                Ok(system)
            }
        }
    }
}

cbor_read!(Numberer<String>);

pub trait CborWrite {
    fn to_cbor_write<W>(&self, write: &mut W) -> Result<()>
    where
        W: Write;
}

// impl<T> CborWrite for Numberer<T>
// where
//     T: Eq + Hash + Serialize + Deserialize,
// {
//     fn to_cbor_write<W>(&self, write: &mut W) -> Result<()>
//     where
//         W: Write,
//     {
//         let data = serde_cbor::to_vec(self)?;
//         write.write(&data)?;
//         Ok(())
//     }
// }

macro_rules! cbor_write {
    ($type: ty) => {
        impl CborWrite for $type {
            fn to_cbor_write<W>(&self, write: &mut W) -> Result<()>
                where W: Write
            {
                let data = serde_cbor::to_vec(self)?;
                write.write(&data)?;
                Ok(())
            }
        }
    }
}

cbor_write!(Numberer<String>);